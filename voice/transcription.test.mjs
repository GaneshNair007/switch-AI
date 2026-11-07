import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareSpeech,detectSpeech,confidentTranscript,normalizeFloorId} from './transcription.mjs';

test('silence, low noise and short clicks never reach speech provider',()=>{
  assert.equal(prepareSpeech(Buffer.alloc(48000*4)),null);
  const noise=Buffer.alloc(48000*4);for(let i=0;i<noise.length;i+=2)noise.writeInt16LE(i%4?25:-25,i);
  assert.equal(prepareSpeech(noise),null);
  noise.writeInt16LE(20000,0);assert.equal(prepareSpeech(noise),null);
});
test('speech preflight produces 16kHz mono without losing a stereo channel',()=>{
  const pcm=Buffer.alloc(48000*4);for(let i=0;i<48000;i++)pcm.writeInt16LE(Math.round(4000*Math.sin(i*Math.PI/60)),i*4);
  const result=prepareSpeech(pcm);assert.ok(result.speechMs>900);assert.equal(result.pcm.length,32000);
  assert.ok(result.pcm.some(v=>v!==0));
});
test('provider silence and uncertain segments are rejected, legitimate thanks preserved',()=>{
  const good={text:'Thank you.',no_speech_prob:0.01,avg_logprob:-0.2,compression_ratio:1};
  assert.equal(confidentTranscript({segments:[good]}),'Thank you.');
  assert.equal(confidentTranscript({segments:[{...good,no_speech_prob:0.9}]}),'');
  assert.equal(confidentTranscript({segments:[{...good,avg_logprob:-2}]}),'');
  assert.equal(confidentTranscript({text:'Unverified text'}),'');
  assert.equal(confidentTranscript({segments:[{...good,text:'.'}]}),'');
  assert.equal(confidentTranscript({segments:[{...good,no_speech_prob:0.3}]}),'');
});
test('WebRTC detector rejects silence and sustained microphone-like noise',()=>{
  assert.equal(detectSpeech(Buffer.alloc(32000)).accepted,false);
  const noise=Buffer.alloc(32000);let seed=12345;
  for(let i=0;i<16000;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;noise.writeInt16LE(Math.round((seed/2**32-.5)*5000),i*2);}
  assert.equal(detectSpeech(noise).accepted,false);
});
test('grant accepts pasted full ID or missing prefix and explains invalid input',()=>{
  const id='f4c217a28a084dc5aac19cc3d5aaf07c';
  assert.equal(normalizeFloorId(id),'floor-'+id);assert.equal(normalizeFloorId('floor-'+id),'floor-'+id);
  assert.throws(()=>normalizeFloorId(''),/Copy the request ID/);
});
