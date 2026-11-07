import test from 'node:test';
import assert from 'node:assert/strict';
import {pcmToWav,wavToStereo48k,PlaybackGate} from './audio.mjs';

test('PCM WAV roundtrip and resampling preserve channel data',()=>{
 const pcm=Buffer.alloc(1920);for(let i=0;i<960;i++)pcm.writeInt16LE(i%100,i*2);
 assert.deepEqual(wavToStereo48k(pcmToWav(pcm)),pcm);
 const mono=Buffer.alloc(480);mono.writeInt16LE(200,0);
 const stereo=wavToStereo48k(pcmToWav(mono,24000,1));assert.equal(stereo.length,1920);assert.equal(stereo.readInt16LE(0),200);assert.equal(stereo.readInt16LE(2),200);
});
test('truncated or unsupported audio fails explicitly',()=>{assert.throws(()=>wavToStereo48k(Buffer.from('bad')));const bad=pcmToWav(Buffer.alloc(8));bad.writeUInt16LE(3,20);assert.throws(()=>wavToStereo48k(bad));});
test('Groq streaming WAV unknown data size is decoded while actual truncation is rejected',()=>{
 const pcm=Buffer.alloc(4800);pcm.writeInt16LE(1000,0);
 const wav=pcmToWav(pcm,24000,1);wav.writeUInt32LE(0xffffffff,4);wav.writeUInt32LE(0xffffffff,40);
 assert.equal(wavToStereo48k(wav).length,19200);
 const truncated=pcmToWav(pcm,24000,1).subarray(0,100);assert.throws(()=>wavToStereo48k(truncated),/Truncated/);
});
test('human interruption invalidates pending TTS and prevents double speakers',()=>{
 let stops=0;const gate=new PlaybackGate(()=>stops++);const epoch=gate.begin('request-1');assert.throws(()=>gate.begin('request-2'));assert.equal(gate.interrupt(),'request-1');assert.equal(gate.valid(epoch),false);const next=gate.begin('request-2');assert.equal(gate.valid(next),true);assert.equal(stops,1);
});

test('installed Opus codec can encode and decode Discord PCM frames',async()=>{
 const {default:OpusScript}=await import('opusscript');
 const codec=new OpusScript(48000,2,OpusScript.Application.AUDIO);
 const pcm=Buffer.alloc(960*2*2);
 const packet=codec.encode(pcm,960);
 assert.ok(packet.length>0);
 assert.equal(codec.decode(packet).length,pcm.length);
 codec.delete();
});
