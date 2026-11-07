import {Client, GatewayIntentBits} from 'discord.js';
import {joinVoiceChannel,createAudioPlayer,createAudioResource,AudioPlayerStatus,VoiceConnectionStatus,entersState,EndBehaviorType,StreamType} from '@discordjs/voice';
import prism from 'prism-media';
import {Readable} from 'node:stream';
import {randomUUID} from 'node:crypto';
import {pcmToWav,wavToStereo48k,PlaybackGate} from './audio.mjs';

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
  const response=await fetch('https://api.groq.com/openai/v1/audio/'+endpoint,{method:'POST',headers:{Authorization:'Bearer '+env.GROQ_API_KEY,...(json?{'Content-Type':'application/json'}:{})},body:json?JSON.stringify(body):body,signal:AbortSignal.timeout(30000)});
  if(!response.ok) throw new Error(`Speech provider HTTP ${response.status}`);return response;
}
async function transcribe(pcm) {
  const form=new FormData();form.set('model',env.GROQ_STT_MODEL||'whisper-large-v3-turbo');form.set('file',new Blob([pcmToWav(pcm)],{type:'audio/wav'}),'utterance.wav');
  return (await (await speechRequest('transcriptions',form)).json()).text;
}
async function synthesize(text) {
  if(!text||text.length>200) throw new Error('Speech must contain 1–200 characters');
  const response=await speechRequest('speech',{model:env.GROQ_TTS_MODEL||'canopylabs/orpheus-v1-english',voice:env.GROQ_TTS_VOICE||'troy',input:text,response_format:'wav'},true);
  return wavToStereo48k(Buffer.from(await response.arrayBuffer()));
}
async function announce(m,text) {await m.channel.send({content:text.slice(0,1900),allowedMentions:{parse:[]}});}
async function interrupt(m,userId) {
  const active=m.gate.interrupt();
  if(active) await api(userId,'release',{meeting_id:m.id,request_id:active});
}
function receive(m,userId) {
  // Every human voice activity stops playback, even if that participant did not consent to transcription.
  const active=m.gate.interrupt();
  if(active) api(m.hostId,'release',{meeting_id:m.id,request_id:active}).catch(e=>announce(m,'Floor release failed: '+e.message));
  if(!m.consents.has(userId)||m.captures.has(userId)||meeting!==m) return;
  const source=m.connection.receiver.subscribe(userId,{end:{behavior:EndBehaviorType.AfterSilence,duration:700}});
  const decoder=new prism.opus.Decoder({rate:48000,channels:2,frameSize:960});
  const chunks=[];let size=0,finished=false;
  const finish=async()=>{
    if(finished)return;finished=true;clearTimeout(timer);m.captures.delete(userId);source.destroy();decoder.destroy();
    if(!m.consents.has(userId)||meeting!==m||size<19200)return;
    if(m.pending>=2){await announce(m,'Transcription queue full; this utterance was not processed.');return;}
    m.pending++;
    try {
      const text=await transcribe(Buffer.concat(chunks));
      if(!m.consents.has(userId)||meeting!==m)return;
      const result=await api(userId,'transcript',{meeting_id:m.id,event_id:randomUUID(),text});
      await announce(m,`Transcript <@${userId}>: ${text}`);
      if(result.request) await announce(m,`✋ ${result.request.reason}\nGrant with !voice grant ${result.request.request_id}`);
    } catch(e) {await announce(m,'Voice processing failed: '+e.message);} finally {m.pending--;chunks.length=0;}
  };
  const timer=setTimeout(finish,15000);
  m.captures.set(userId,()=>{chunks.length=0;size=0;finish();});
  decoder.on('data',chunk=>{size+=chunk.length;if(size<=2880000)chunks.push(chunk);else finish();});
  decoder.on('end',finish);decoder.on('error',e=>{announce(m,'Audio decode failed: '+e.message);size=0;finish();});
  source.on('error',()=>{size=0;finish();});source.pipe(decoder);
}
client.on('messageCreate',async message=>{
  if(message.author.bot||message.guildId!==env.DISCORD_GUILD_ID||!message.content.startsWith('!voice '))return;
  const [action,...rest]=message.content.slice(7).trim().split(/\s+/),uid=message.author.id;
  try {
    if(action==='start') {
      if(meeting||starting)throw new Error('A meeting is already active or connecting');
      const channel=message.member.voice.channel;if(!channel)throw new Error('Join a voice channel first');
      starting=true;
      let record,connection;
      try {
      record=await api(uid,'start',{title:rest.join(' ')||'Engineering meeting'});
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
    else if(action==='grant') {
      const requestId=rest[0],epoch=m.gate.begin(requestId);let granted=false;
      try {
        const grant=await api(uid,'grant',{meeting_id:m.id,request_id:requestId});if(!grant.granted && grant.state!=='granted')throw new Error(grant.reason);granted=true;
        const {script}=await api(uid,'script',{meeting_id:m.id,request_id:requestId});const pcm=await synthesize(script);
        if(!m.gate.valid(epoch))return;
        await api(uid,'speak',{meeting_id:m.id,request_id:requestId});if(!m.gate.valid(epoch))return;
        m.player.play(createAudioResource(Readable.from([pcm]),{inputType:StreamType.Raw}));
        await entersState(m.player,AudioPlayerStatus.Playing,5000);
        await entersState(m.player,AudioPlayerStatus.Idle,60000);
      } finally {if(m.gate.valid(epoch))m.gate.interrupt();if(granted)await api(uid,'release',{meeting_id:m.id,request_id:requestId});}
    }
    else if(action==='interrupt')await interrupt(m,uid);
    else if(action==='stop') {const summary=await api(uid,'end',{meeting_id:m.id});meeting=null;m.gate.interrupt();for(const cancel of m.captures.values())cancel();m.connection.destroy();await announce(m,JSON.stringify(summary));}
    else throw new Error('Use start, consent, revoke, grant, interrupt or stop');
  } catch(e) {await message.reply({content:'Voice action failed: '+e.message,allowedMentions:{parse:[]}});}
});
client.on('error',e=>console.error('Discord gateway error:',e.name));
process.on('SIGINT',()=>{if(meeting){meeting.gate.interrupt();meeting.connection.destroy();}client.destroy();process.exit(0);});
await client.login(env.DISCORD_VOICE_BOT_TOKEN);
