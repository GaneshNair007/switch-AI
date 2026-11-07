"""Durable projections; Switch handoffs remain authoritative on Switch."""
import json
import time
import threading
import hashlib
from pathlib import Path
from .discord_setup import DiscordREST, MAP_PATH


class Notifications:
    def __init__(self,workflow,discord=None):self.w=workflow;self.discord=discord;self.lock=threading.Lock()

    def flush(self):
        with self.lock:
            workers=getattr(self.w,'switch_workers',[])
            for item in self.w.store.list('switch_notification'):
                if item.get('investigation_started') or item.get('attempts',0)>=5 or item.get('next_attempt',0)>time.time():continue
                clerk=next((w for w,t in workers if w.role=='clerk' and w.client.connected and t.is_alive() and
                    (not item.get('switch_room_id') or w.client.room_id==item['switch_room_id'])),None)
                if not clerk:continue
                item['attempts']=item.get('attempts',0)+1
                try:
                    if item['status']!='DELIVERED':
                        receipt=clerk.client.post_message(item['content'])
                        if not receipt.get('event_id'):raise ValueError('Switch returned no delivery receipt')
                        item.update(status='DELIVERED',receipt=receipt)
                    self.w.store.put('switch_notification',item.get('notification_id',item['case_id']),item)
                except Exception as exc:
                    item.update(status='FAILED_OR_UNKNOWN',error_type=type(exc).__name__,next_attempt=time.time()+2**item['attempts'])
                    self.w.store.put('switch_notification',item.get('notification_id',item['case_id']),item);continue
                if hasattr(clerk,'begin'):
                    try:clerk.begin(item);item['investigation_started']=True
                    except Exception as exc:
                        item['investigation_error']=type(exc).__name__;item['next_attempt']=time.time()+2**item['attempts']
                        self.w.store.event('switch.investigation_failed',item['case_id'],'dispatcher',{'error_type':type(exc).__name__})
                else:item['investigation_started']=True
                self.w.store.put('switch_notification',item.get('notification_id',item['case_id']),item)
                if not item.get('mission_id'):
                    for channel in ('dev-watch','case-docket'):
                        key=item['case_id']+':'+channel
                        self.w.store.put('discord_outbox',key,{'id':key,'channel':channel,'correlation_id':item['case_id'],'content':item['content'],'status':'PENDING','attempts':0})
            if not self.discord or not MAP_PATH.exists():return
            mapping=json.loads(MAP_PATH.read_text())['channels']
            for item in self.w.store.list('discord_outbox'):
                if item['status']=='DELIVERED' or item.get('attempts',0)>=5 or item.get('next_attempt',0)>time.time():continue
                channel=item.get('destination_id') or mapping.get(item['channel'])
                if not channel:continue
                item['attempts']=item.get('attempts',0)+1
                try:
                    body={'content':item['content'][:1900],'allowed_mentions':{'parse':[]},
                          'nonce':hashlib.sha256(item['id'].encode()).hexdigest()[:24],'enforce_nonce':True}
                    if len(item['content'])>1900:
                        body['content']=f"[{item['correlation_id']}] Complete record attached."
                        result=self.discord.call('POST',f'/channels/{channel}/messages',body,
                            attachment=(item.get('attachment_name','shipcourt-record.txt'),item['content']))
                    else:result=self.discord.call('POST',f'/channels/{channel}/messages',body)
                    if not result.get('id'):raise ValueError('Discord returned no message ID')
                    item.update(status='DELIVERED',receipt={'message_id':result['id'],'channel_id':channel})
                    self.w.store.event('discord.notification_delivered',item['correlation_id'],'dispatcher',{'receipt':item['receipt']},source_platform='discord')
                    mission=self.w.store.get('mission',item['correlation_id'])
                    if mission and item['channel']=='mission-control' and not mission.get('discord_thread_id'):
                        try:
                            thread=self.discord.call('POST',f"/channels/{channel}/messages/{result['id']}/threads",
                                {'name':mission['title'][:90],'auto_archive_duration':1440})
                            if thread.get('id'):
                                with self.w.workspace.lock:
                                    mission=self.w.store.get('mission',mission['mission_id'])
                                    mission['discord_thread_id']=thread['id'];self.w.store.put('mission',mission['mission_id'],mission)
                        except Exception as exc:self.w.store.event('discord.thread_unavailable',mission['mission_id'],'dispatcher',{'error_type':type(exc).__name__})
                except Exception as exc:item.update(status='FAILED_OR_UNKNOWN',error_type=type(exc).__name__,next_attempt=time.time()+2**item['attempts'])
                self.w.store.put('discord_outbox',item['id'],item)

    def run(self):
        while True:
            try:self.flush()
            except Exception as exc:self.w.store.event('notifications.failed','workspace','dispatcher',{'error_type':type(exc).__name__})
            time.sleep(3)
