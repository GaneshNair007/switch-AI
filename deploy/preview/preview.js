'use strict';
const tabs=[...document.querySelectorAll('[role="tab"]')];
function activate(tab){
  for(const item of tabs){
    const active=item===tab;
    item.setAttribute('aria-selected',String(active));
    item.tabIndex=active?0:-1;
    document.getElementById(item.getAttribute('aria-controls')).hidden=!active;
  }
}
for(const tab of tabs){
  tab.addEventListener('click',()=>activate(tab));
  tab.addEventListener('keydown',event=>{
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();
    const index=event.key==='Home'?0:event.key==='End'?tabs.length-1:
      (tabs.indexOf(tab)+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    activate(tabs[index]);tabs[index].focus();
  });
}
