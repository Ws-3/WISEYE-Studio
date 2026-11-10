"""Live inventory changes without map travel or resetting other aircraft.

Four bounded, landed physics slots match WISEYE's four-aircraft limit. Unused
slots are hidden outside the active scene, with no camera capture or topic subscription.
"""
import asyncio
import uuid
import copy
import math
from contextlib import suppress
from core.live_devices import from_state, apply


class LiveFleetMixin:
    async def _native(self,command,payload=None):
        reply=await asyncio.to_thread(self.rpc,command,payload)
        if not reply or reply.get('status')!='ok':
            raise ValueError((reply or {}).get('error',{}).get('message','UE did not acknowledge the scene edit'))
        return reply['payload']

    async def publish_rotors(self):
        while not self.closed:
            import time
            for ctl in list(self.controllers.values()):
                if getattr(ctl,'airframe',None)=='fixedwing':continue
                sampled,_,rpms=ctl.rotor_sample
                fresh=sampled>0 and time.monotonic()-sampled<1
                await asyncio.to_thread(ctl.ue_request,'rotors.sync_state',dict(rpm=list(rpms) if fresh else [0]*4,fresh=fresh))
            await asyncio.sleep(.1)

    async def watch_ue_controls(self):
        misses=0
        while not self.closed:
            try:state=await self._native('flight.get_local_control')
            except ValueError:
                if await asyncio.to_thread(self.listener_open):
                    await asyncio.sleep(.5);continue
                misses+=1
                if misses>=3:raise self.session_changed('UE Play session ended')
                await asyncio.sleep(.5);continue
            if state['play_session_id']!=self.run_id:raise self.session_changed('UE scene changed')
            misses=0
            selected=self.controllers.get(state.get('controlled_drone_id','uav-01'))
            if selected:
                for command in state['commands']:
                    try:
                        if command=='flight.toggle_mode':await selected.execute('flight.set_mode',dict(mode='manual' if selected.mode=='auto' else 'auto'))
                        elif command=='sim.toggle_pause':await selected.execute('sim.resume' if selected.paused else 'sim.pause',{})
                        elif command=='sim.reset':await selected.execute(command,{})
                    except (ValueError,KeyError) as error:print('Local command rejected:',error,flush=True)
                if state['input_dirty'] and selected.mode=='manual' and not selected.paused:
                    with suppress(ValueError):await selected.execute('flight.set_input',{k:state[k] for k in ('forward','right','up','yaw')})
            await asyncio.sleep(.1)

    async def _set_pose(self,robot,item):
        original=await asyncio.to_thread(robot.get_ground_truth_pose)
        yaw=math.radians(item['rotation_deg'][1]);x,y,z=item['position_cm']
        pose=dict(frame_id=original.get('frame_id','DEFAULT_FRAME'),translation=dict(x=x/100,y=y/100,z=-z/100),
                  rotation=dict(w=math.cos(yaw/2),x=0,y=0,z=math.sin(yaw/2)))
        await self._write_pose(robot,pose)
        return original

    async def _write_pose(self,robot,pose):
        lease=dict(run_id=self.run_id,slot=robot.name,token=uuid.uuid4().hex)
        await self._native('flight.prepare_slot',lease)
        try:
            if await asyncio.to_thread(robot.set_pose,pose,True) is not True:raise ValueError('Physics refused placement')
            # Allow the renderer to receive the authoritative teleport without a
            # collision sweep across the intervening city buildings.
            await asyncio.sleep(.15)
        finally:
            await self._native('flight.finish_slot',lease)

    async def _retire(self,ident):
        ctl=self.controllers.pop(ident,None)
        if not ctl:return
        await ctl.close(skip_remote=True)
        if getattr(ctl,'airframe',None)!='fixedwing':
            self.client.unsubscribe([ctl.drone.robot_info['rotor_info'],ctl.drone.robot_info['actual_pose']])

    async def _create(self,item,snapshot,slot):
        device=dict(item,dynamics_name=slot,initial_position_cm=item['position_cm'])
        if item['model_id']=='fixedwing':ctl=self.fixedwing_type(self.world,device,snapshot)
        else:
            ctl=self.controller_type(self.world,self.pool[slot],0,3.,ready_on_ground=True,device_id=item['id'])
            await asyncio.to_thread(ctl.initialize_route)
            self.client.subscribe(ctl.drone.robot_info['rotor_info'],ctl.on_rotors)
            self.client.subscribe(ctl.drone.robot_info['actual_pose'],ctl.on_pose)
        ctl.scene_id=self.scene_id;ctl.play_session_id=self.run_id;ctl.fleet_controllers=self.controllers
        self.controllers[item['id']]=ctl;ctl.start()
        if item['model_id']!='fixedwing':await asyncio.to_thread(ctl.ue_request,'flight.sync_state',dict(mode=ctl.mode,paused=ctl.paused))

    async def edit_devices(self,payload):
        async with self.edit_lock:
            if self.closed:raise ValueError('Flight service is closing')
            snapshot=await self._native('sim.get_state')
            if (payload.get('run_id')!=snapshot['run_id'] or payload.get('scene_id')!=snapshot['scene_id'] or
                payload.get('expected_revision')!=snapshot.get('fleet_revision',0)):
                raise ValueError('Device list changed; reread the current scene')
            before=from_state(snapshot);desired=apply(before,payload.get('changes'))
            old={d['id']:d for d in before['devices']};new={d['id']:d for d in desired['devices']}
            operations=copy.deepcopy(payload['changes'])
            slots=dict(self.slots)
            for patch in operations:
                ident=patch['id'];previous=old.get(ident);item=new.get(ident)
                if previous and previous['kind']=='drone':
                    ctl=self.controllers[ident]
                    crossing=item and (previous['model_id']=='fixedwing')!=(item['model_id']=='fixedwing')
                    protected=patch['action']=='remove' or crossing or 'position_cm' in patch or 'rotation_deg' in patch
                    status=ctl.state()
                    if protected and (status['flight_status']!='ready' or status.get('command_active') or any(rpm>1 for rpm in status.get('motor_rpm',[]))):
                        raise ValueError('Stop or land only the edited UAV before moving/removing/changing its airframe')
                    if crossing:
                        patch.setdefault('position_cm',copy.deepcopy(item['position_cm']))
                        patch.setdefault('rotation_deg',copy.deepcopy(item['rotation_deg']))
                if patch['action']=='remove':slots.pop(ident,None)
            for patch in operations:
                item=new.get(patch['id'])
                if patch['action']=='add' and item['kind']=='drone':
                    slots[item['id']]=next((f'Drone{i}' for i in range(1,5) if f'Drone{i}' not in slots.values()),None)
                    if slots[item['id']] is None:raise ValueError('All four flight slots are occupied')
                    patch['dynamics_name']=slots[item['id']]
            old_slots=dict(self.slots)
            released={old_slots[p['id']] for p in operations if p['id'] in old and old[p['id']]['kind']=='drone' and old[p['id']]['model_id']!='fixedwing' and (p['action']=='remove' or new[p['id']]['model_id']=='fixedwing')}
            moved=[]
            try:
                for patch in operations:
                    ident=patch['id'];item=new.get(ident);previous=old.get(ident)
                    if not item or item['kind']!='drone' or item['model_id']=='fixedwing':continue
                    crossing=previous and previous['model_id']=='fixedwing'
                    if patch['action']=='add' or crossing or 'position_cm' in patch or 'rotation_deg' in patch:
                        robot=self.pool[slots[ident]]
                        moved.append((robot,await self._set_pose(robot,item)))
                if self.closed:raise ValueError('Flight service is closing')
                args=dict(run_id=self.run_id,scene_id=self.scene_id,expected_revision=payload['expected_revision'],changes=operations)
                reply=None
                for _ in range(20):
                    reply=await asyncio.to_thread(self.rpc,'fleet.patch',args)
                    if reply and reply.get('status')=='ok':break
                    if 'flight controller first' not in (reply or {}).get('error',{}).get('message',''):break
                    await asyncio.sleep(.05)
                if not reply or reply.get('status')!='ok':raise ValueError((reply or {}).get('error',{}).get('message','Live scene edit not acknowledged'))
            except Exception:
                for robot,pose in reversed(moved):
                    with suppress(Exception):await self._write_pose(robot,pose)
                raise
            final=reply['payload']
            for patch in operations:
                ident=patch['id'];item=new.get(ident);previous=old.get(ident)
                if (previous or item)['kind']!='drone':continue
                crossing=previous and item and (previous['model_id']=='fixedwing')!=(item['model_id']=='fixedwing')
                if patch['action']=='remove' or crossing:await self._retire(ident)
                if item and (patch['action']=='add' or crossing):await self._create(item,final,slots[ident])
                elif item and ('position_cm' in patch or 'rotation_deg' in patch):
                    ctl=self.controllers[ident]
                    if getattr(ctl,'airframe',None)!='fixedwing':await asyncio.to_thread(ctl.initialize_route)
            self.slots=slots
            # Release unused dynamics without touching any other vehicle's task.
            used={slots[i] for i,c in self.controllers.items() if getattr(c,'airframe',None)!='fixedwing'}
            for slot,robot in self.pool.items():
                if slot in released and slot not in used:
                    await self._set_pose(robot,dict(position_cm=[500000+int(slot[-1])*500,500000,5000],rotation_deg=[0,0,0]))
            await self._native('flight.hide_reserves')
            result=self.state(payload.get('device_id','uav-01') if payload.get('device_id','uav-01') in self.controllers else 'uav-01')
            result['fleet_revision']=final['fleet_revision'];result['live_devices']=final['devices']
            return result
