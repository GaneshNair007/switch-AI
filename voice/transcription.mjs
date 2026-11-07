import createVAD, {VADMode, VADEvent} from '@ozymandiasthegreat/vad';
const VAD = await createVAD();
// Energy preflight is followed by WebRTC speech detection before upload.
export function prepareSpeech(pcm, minRms=160, minSpeechMs=240) {
  if(pcm.length%4) throw new Error('Expected stereo PCM16 frames');
  const frames=pcm.length/4,mono=Buffer.alloc(Math.floor(frames/3)*2);
  let voiced=0,peak=0;
  for(let start=0;start<frames;start+=960) {
    const end=Math.min(frames,start+960);let energy=0;
    for(let i=start;i<end;i++) {
      const left=pcm.readInt16LE(i*4),right=pcm.readInt16LE(i*4+2);
      energy+=(left*left+right*right)/2;peak=Math.max(peak,Math.abs(left),Math.abs(right));
    }
    if(Math.sqrt(energy/(end-start))>=minRms)voiced+=end-start;
  }
  if(voiced/48<minSpeechMs)return null;
  for(let i=0;i<mono.length/2;i++) {
    let sum=0;for(let j=0;j<3;j++){const pos=(i*3+j)*4;sum+=pcm.readInt16LE(pos)+pcm.readInt16LE(pos+2);}
    mono.writeInt16LE(Math.round(sum/6),i*2);
  }
  return {pcm:mono,speechMs:voiced/48,peak};
}

export function detectSpeech(pcm) {
  const detector=new VAD(VADMode.VERY_AGGRESSIVE,16000),frame=new Int16Array(320);
  let voiced=0,total=0,run=0,longest=0;
  try {
    for(let offset=0;offset+640<=pcm.length;offset+=640) {
      for(let i=0;i<320;i++)frame[i]=pcm.readInt16LE(offset+i*2);
      const event=detector.processFrame(frame);total++;
      if(event===VADEvent.ERROR)throw new Error('Voice activity detection failed');
      if(event===VADEvent.VOICE){voiced++;run++;longest=Math.max(longest,run);}else run=0;
    }
  } finally {detector.destroy();}
  return {accepted:voiced>=12&&longest>=6&&voiced/Math.max(total,1)>=0.2,voicedMs:voiced*20,totalMs:total*20};
}

export function confidentTranscript(result) {
  const segments=result.segments;
  if(!Array.isArray(segments)||!segments.length)return '';
  return segments.filter(s=>Number.isFinite(s.no_speech_prob)&&Number.isFinite(s.avg_logprob)
    &&s.no_speech_prob<0.6&&s.avg_logprob>-1&&(!Number.isFinite(s.compression_ratio)||s.compression_ratio<2.4)
    &&/[\p{L}\p{N}]/u.test(s.text||'')
    &&((s.text||'').trim().split(/\s+/).length>=3||(s.no_speech_prob<0.1&&s.avg_logprob>-0.5)))
    .map(s=>s.text.trim()).filter(Boolean).join(' ').trim();
}

export function normalizeFloorId(value) {
  const id=String(value||'').trim();
  if(/^(floor-)?[a-f0-9]{32}$/.test(id))return id.startsWith('floor-')?id:'floor-'+id;
  throw new Error('Copy the request ID from the hand message: !voice grant floor-…');
}
