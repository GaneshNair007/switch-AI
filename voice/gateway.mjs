import {Client, GatewayIntentBits,ActionRowBuilder,ButtonBuilder,ButtonStyle} from 'discord.js';
import {readFileSync} from 'node:fs';
import {joinVoiceChannel,createAudioPlayer,createAudioResource,AudioPlayerStatus,VoiceConnectionStatus,entersState,EndBehaviorType,StreamType} from '@discordjs/voice';
import prism from 'prism-media';
import {Readable} from 'node:stream';
import {randomUUID} from 'node:crypto';
import {pcmToWav,wavToStereo48k,PlaybackGate} from './audio.mjs';
import {prepareSpeech,detectSpeech,confidentTranscript,normalizeFloorId} from './transcription.mjs';

const env=process.env;
for(const key of ['DISCORD_VOICE_BOT_TOKEN','DISCORD_GUILD_ID','SHIPCOURT_VOICE_TOKEN','GROQ_API_KEY']) if(!env[key]) throw new Error(`Missing ${key}`);
const backend=env.SHIPCOURT_URL||'http://127.0.0.1:8080';
const backendUrl=new URL(backend);
if(backendUrl.protocol!=='https:' && !['localhost','127.0.0.1'].includes(backendUrl.hostname)) throw new Error('Backend requires HTTPS outside localhost');
const client=new Client({intents:[GatewayIntentBits.Guilds,GatewayIntentBits.GuildVoiceStates,GatewayIntentBits.GuildMessages,GatewayIntentBits.MessageContent]});
let meeting=null,starting=false;
async function api(userId,action,args={}) {
  const response=await fetch(backend+'/api/voice/action',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+env.SHIPCOURT_VOICE_TOKEN},
    body:JSON.stringify({guild_id:env.DISCORD_GUILD_ID,user_id:userId,action,args:{meeting_id:meeting?.id,...args}}),signal:AbortSignal.timeout(120000)});
  const result=await response.json();if(!response.ok) throw new Error(result.error||'Backend rejected action');return result;
}
async function speechRequest(endpoint,body,json=false) {
  const response=await fetch('https://api.groq.com/openai/v1/audio/'+endpoint,{method:'POST',headers:{Authorization:'Bearer '+env.GROQ_API_KEY,'User-Agent':'ShipCourt/1.0',...(json?{'Content-Type':'application/json'}:{})},body:json?JSON.stringify(body):body,signal:AbortSignal.timeout(30000)});
  if(!response.ok) throw new Error(`Speech provider HTTP ${response.status}`);return response;
}
async function transcribe(pcm) {
  const speech=prepareSpeech(pcm);
  if(!speech)return '';
  const activity=detectSpeech(speech.pcm);
  if(!activity.accepted){console.log('Skipped non-speech audio:',JSON.stringify(activity));return '';}
  const form=new FormData();form.set('model',env.GROQ_STT_MODEL||'whisper-large-v3');
  form.set('file',new Blob([pcmToWav(speech.pcm,16000,1)],{type:'audio/wav'}),'utterance.wav');
  form.set('language',env.GROQ_STT_LANGUAGE||'en');form.set('temperature','0');form.set('response_format','verbose_json');
  const result=await (await speechRequest('transcriptions',form)).json();
  const text=confidentTranscript(result);
  console.log('Transcription quality:',JSON.stringify({voiced_ms:activity.voicedMs,segments:result.segments?.length||0,accepted:!!text}));
  return text;
}
async function synthesize(text) {
  if(!text||text.length>200) throw new Error('Speech must contain 1–200 characters');
  const response=await speechRequest('speech',{model:env.GROQ_TTS_MODEL||'canopylabs/orpheus-v1-english',voice:env.GROQ_TTS_VOICE||'troy',input:text,response_format:'wav'},true);
  return wavToStereo48k(Buffer.from(await response.arrayBuffer()));
}
async function announce(m,text) {await m.channel.send({content:text.slice(0,1900),allowedMentions:{parse:[]}});}
function channelId(name){try{return JSON.parse(readFileSync(new URL('../.runtime/discord_channels.json',import.meta.url),'utf8')).channels[name];}catch{return null;}}
async function hand(m,request){
  const target=channelId('meeting-floor'),channel=target?await client.channels.fetch(target):m.channel;
  const actions=[['Grant Floor','grant'],['Text Instead','text'],['Dismiss','dismiss'],['Interrupt','interrupt'],['Mute Agent','mute']];
  const row=new ActionRowBuilder().addComponents(actions.map(([label,action])=>new ButtonBuilder().setLabel(label).setCustomId(`floor:${m.id}:${action}:${request.request_id}`).setStyle(action==='grant'?ButtonStyle.Primary:ButtonStyle.Secondary)));
  const end=new ActionRowBuilder().addComponents(new ButtonBuilder().setLabel('End Meeting').setCustomId(`floor:${m.id}:stop:${request.request_id}`).setStyle(ButtonStyle.Danger));
  await channel.send({content:`✋ [${m.id}] ${request.agent_id}: ${request.reason}\nPriority ${request.priority} · State ${request.state} · Expires <t:${Math.floor(request.expires_at)}:R>\nEvidence: ${request.evidence_refs.join(', ')}`,components:[row,end],allowedMentions:{parse:[]}});
}
async function interrupt(m,userId) {
  const active=m.gate.interrupt();
  if(active) await api(userId,'release',{meeting_id:m.id,request_id:active});
}
function receive(m,userId) {
  // Every human voice activity stops playback, even if that participant did not consent to transcription.
  const active=m.gate.interrupt();
  if(active) api(m.hostId,'release',{meeting_id:m.id,request_id:active}).catch(e=>announce(m,'Floor release failed: '+e.message));
  if(!m.consents.has(userId)||m.captures.has(userId)||meeting!==m) return;
  const source=m.connection.receiver.subscribe(userId,{end:{behavior:EndBehaviorType.AfterSilence,duration:1000}});
  const decoder=new prism.opus.Decoder({rate:48000,channels:2,frameSize:960});
  const chunks=[];let size=0,finished=false;
  const finish=async()=>{
    if(finished)return;finished=true;clearTimeout(timer);m.captures.delete(userId);source.destroy();decoder.destroy();
    if(!m.consents.has(userId)||meeting!==m||size<19200)return;
    if(m.pending>=2){await announce(m,'Transcription queue full; this utterance was not processed.');return;}
    m.pending++;
    try {
      const text=await transcribe(Buffer.concat(chunks));
      if(!text||!m.consents.has(userId)||meeting!==m)return;
      const result=await api(userId,'transcript',{meeting_id:m.id,event_id:randomUUID(),text});
      await announce(m,`Transcript <@${userId}>: ${text}`);
      if(result.request) await hand(m,result.request);
    } catch(e) {await announce(m,'Voice processing failed: '+e.message);} finally {m.pending--;chunks.length=0;}
  };
  const timer=setTimeout(finish,15000);
  m.captures.set(userId,()=>{chunks.length=0;size=0;finish();});
  decoder.on('data',chunk=>{size+=chunk.length;if(size<=2880000)chunks.push(chunk);else finish();});
  decoder.on('end',finish);decoder.on('error',e=>{announce(m,'Audio decode failed: '+e.message);size=0;finish();});
  source.on('error',()=>{size=0;finish();});source.pipe(decoder);
}
async function handleVoice(message,action,rest){
  const uid=message.author.id;
  try {
    if(action==='start') {
      if(meeting||starting)throw new Error('A meeting is already active or connecting');
      const channel=message.member.voice.channel;if(!channel)throw new Error('Join a voice channel first');
      starting=true;
      let record,connection;
      try {
      record=await api(uid,'start',{title:rest.join(' ')||'Engineering meeting',...(rest[0]?.startsWith('MISSION-')?{mission_id:rest[0]}:{})});
      connection=joinVoiceChannel({channelId:channel.id,guildId:message.guild.id,adapterCreator:message.guild.voiceAdapterCreator,selfDeaf:false});
      await entersState(connection,VoiceConnectionStatus.Ready,20000);
      const player=createAudioPlayer();connection.subscribe(player);
      const m={id:record.meeting_id,hostId:uid,channel:message.channel,connection,player,consents:new Set(),captures:new Map(),pending:0};
      m.gate=new PlaybackGate(()=>player.stop(true));meeting=m;
      connection.receiver.speaking.on('start',id=>{if(id!==client.user.id)receive(m,id);});
      connection.on('error',e=>announce(m,'Voice connection failed: '+e.message));
      player.on('error',e=>{interrupt(m,uid).catch(()=>{});announce(m,'Playback failed: '+e.message);});
      await announce(m,'Meeting connected. No transcription until you type !voice consent. Audio goes to Groq for transcription. !voice revoke stops your capture; !voice stop ends the meeting.');
      } catch(error) {
        connection?.destroy();meeting=null;
        if(record)await api(uid,'end',{meeting_id:record.meeting_id});
        throw error;
      } finally {starting=false;}
      return;
    }
    const m=meeting;if(!m)throw new Error('No active meeting');
    if(action==='consent') {await api(uid,'consent',{meeting_id:m.id,enabled:true});m.consents.add(uid);await announce(m,'Consent recorded for <@'+uid+'>.');}
    else if(action==='revoke') {m.consents.delete(uid);m.captures.get(uid)?.();await api(uid,'consent',{meeting_id:m.id,enabled:false});await announce(m,'Transcription stopped for <@'+uid+'>.');}
    else if(action==='grant'||action==='test') {
      const requestId=action==='test'?(await api(uid,'test-request',{meeting_id:m.id})).request_id:normalizeFloorId(rest[0]);
      const epoch=m.gate.begin(requestId);let granted=false;
      try {
        const grant=await api(uid,'grant',{meeting_id:m.id,request_id:requestId});if(!grant.granted && grant.state!=='granted')throw new Error(grant.reason);granted=true;m.grantedRequest=requestId;
        const {script}=await api(uid,'script',{meeting_id:m.id,request_id:requestId});const pcm=await synthesize(script);
        if(!m.gate.valid(epoch))return;
        await api(uid,'speak',{meeting_id:m.id,request_id:requestId});if(!m.gate.valid(epoch))return;
        m.player.play(createAudioResource(Readable.from([pcm]),{inputType:StreamType.Raw}));
        await entersState(m.player,AudioPlayerStatus.Playing,5000);
        await entersState(m.player,AudioPlayerStatus.Idle,60000);
      } finally {if(m.gate.valid(epoch))m.gate.interrupt();if(granted)await api(uid,'release',{meeting_id:m.id,request_id:requestId});if(m.grantedRequest===requestId)m.grantedRequest=null;}
    }
    else if(action==='text'||action==='dismiss'){const result=await api(uid,action,{meeting_id:m.id,request_id:normalizeFloorId(rest[0])});await announce(m,result.contribution||'Floor request dismissed.');}
    else if(action==='interrupt'||action==='mute'){await api(uid,action,{meeting_id:m.id});m.gate.interrupt();await announce(m,action==='mute'?'Agent muted for this meeting.':'Playback interrupted.');}
    else if(action==='stop') {const summary=await api(uid,'end',{meeting_id:m.id});meeting=null;m.gate.interrupt();for(const cancel of m.captures.values())cancel();m.connection.destroy();await announce(m,JSON.stringify(summary));}
    else throw new Error('Use start, consent, revoke, grant, text, dismiss, mute, test, interrupt or stop');
  } catch(e) {await message.reply({content:'Voice action failed: '+e.message,allowedMentions:{parse:[]}});}
}
client.on('messageCreate',async message=>{
  if(message.author.bot||message.guildId!==env.DISCORD_GUILD_ID||!message.content.startsWith('!voice '))return;
  const [action,...rest]=message.content.slice(7).trim().split(/\s+/);await handleVoice(message,action,rest);
});
client.on('interactionCreate',async interaction=>{
  if(!interaction.isButton()||!interaction.customId.startsWith('floor:'))return;
  if(interaction.user.bot||interaction.guildId!==env.DISCORD_GUILD_ID)return;
  await interaction.deferReply({ephemeral:true});
  const [,mid,action,rid]=interaction.customId.split(':');
  if(mid!==meeting?.id){await interaction.editReply('This meeting is no longer active.');return;}
  await interaction.editReply('Processing '+action+'; backend permissions are checked again.');
  await handleVoice({author:interaction.user,guildId:interaction.guildId,guild:interaction.guild,member:interaction.member,channel:interaction.channel,reply:body=>interaction.followUp({...body,ephemeral:true})},action,[rid]);
});
client.on('error',e=>console.error('Discord gateway error:',e.name));
let checkingState=false;
setInterval(async()=>{
  const m=meeting;if(!m||checkingState)return;checkingState=true;
  try {
    const state=await api(m.hostId,'state',{meeting_id:m.id});if(meeting!==m)return;
    if(state.status!=='ACTIVE'){
      meeting=null;m.gate.interrupt();for(const cancel of m.captures.values())cancel();m.connection.destroy();
      await announce(m,'Meeting ended in workspace controls. The persisted recap is queued to #meeting-recaps.');
    } else if(m.gate.active && m.grantedRequest===m.gate.active && !['granted','speaking'].includes(state.requests[m.gate.active]))m.gate.interrupt();
  } catch(e){m.gate.interrupt();console.error('Voice control synchronization failed:',e.message);}
  finally{checkingState=false;}
},2000);
client.once('clientReady',()=>console.log('Voice gateway ready as '+client.user.username+' ('+client.user.id+')'));
process.on('SIGINT',()=>{if(meeting){meeting.gate.interrupt();meeting.connection.destroy();}client.destroy();process.exit(0);});
await client.login(env.DISCORD_VOICE_BOT_TOKEN);
