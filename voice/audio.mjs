// Audio utilities use PCM16; no raw audio is written to disk.
export function pcmToWav(pcm, rate=48000, channels=2) {
  const header=Buffer.alloc(44);
  header.write('RIFF'); header.writeUInt32LE(36+pcm.length,4); header.write('WAVE',8);
  header.write('fmt ',12); header.writeUInt32LE(16,16); header.writeUInt16LE(1,20);
  header.writeUInt16LE(channels,22); header.writeUInt32LE(rate,24);
  header.writeUInt32LE(rate*channels*2,28); header.writeUInt16LE(channels*2,32); header.writeUInt16LE(16,34);
  header.write('data',36); header.writeUInt32LE(pcm.length,40); return Buffer.concat([header,pcm]);
}

export function wavToStereo48k(wav) {
  if(wav.toString('ascii',0,4)!=='RIFF'||wav.toString('ascii',8,12)!=='WAVE') throw new Error('Expected PCM WAV');
  let rate,channels,bits,format,pcm;
  for(let pos=12;pos+8<=wav.length;) {
    const kind=wav.toString('ascii',pos,pos+4),size=wav.readUInt32LE(pos+4),start=pos+8;
    if(start+size>wav.length) throw new Error('Truncated WAV');
    if(kind==='fmt ') {format=wav.readUInt16LE(start);channels=wav.readUInt16LE(start+2);rate=wav.readUInt32LE(start+4);bits=wav.readUInt16LE(start+14);}
    if(kind==='data') pcm=wav.subarray(start,start+size);
    pos=start+size+(size%2);
  }
  if(format!==1||bits!==16||![1,2].includes(channels)||!rate||!pcm) throw new Error('Only mono/stereo PCM16 WAV is supported');
  const frames=Math.floor(pcm.length/(channels*2)),outFrames=Math.floor(frames*48000/rate);
  if(outFrames>48000*60) throw new Error('Speech exceeds one minute');
  const out=Buffer.alloc(outFrames*4);
  for(let i=0;i<outFrames;i++) {
    const x=i*rate/48000,a=Math.min(Math.floor(x),frames-1),b=Math.min(a+1,frames-1),f=x-a;
    for(let ch=0;ch<2;ch++) {const c=Math.min(ch,channels-1),v=pcm.readInt16LE((a*channels+c)*2)*(1-f)+pcm.readInt16LE((b*channels+c)*2)*f;out.writeInt16LE(Math.round(v),i*4+ch*2);}
  }
  return out;
}

export class PlaybackGate {
  constructor(stop) {this.epoch=0;this.active=null;this.stop=stop;}
  begin(requestId) {if(this.active) throw new Error('Floor busy');this.active=requestId;return ++this.epoch;}
  valid(epoch) {return this.active!==null && epoch===this.epoch;}
  interrupt() {const previous=this.active;this.epoch++;this.active=null;this.stop();return previous;}
}
