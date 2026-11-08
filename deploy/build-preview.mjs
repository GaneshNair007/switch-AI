// Explicit public-file allowlist: never publish the checkout or runtime state.
import {mkdir,copyFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,'.runtime','public-preview');
await mkdir(path.join(output,'images'),{recursive:true});
for(const name of ['index.html','style.css','preview.js']){
  await copyFile(path.join(root,'deploy','preview',name),path.join(output,name));
}
for(const name of ['dashboard-command-center.png','discord-mission-control.png']){
  await copyFile(path.join(root,'assets','screenshots',name),path.join(output,'images',name));
}
console.log('Built read-only Ship Court preview: 3 public source files and 2 screenshots. No runtime or credentials included.');
