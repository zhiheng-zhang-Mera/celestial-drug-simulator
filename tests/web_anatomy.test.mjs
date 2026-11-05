import {test} from 'node:test';
import assert from 'node:assert/strict';
import {isVisible, isClick, visualStyle, trackMovement} from '../assets/web/interaction.mjs';

test('hidden ancestor excludes mesh from picking',()=>{
  assert.equal(isVisible({visible:true,parent:{visible:false}}),false);
  assert.equal(isVisible({visible:true,parent:{visible:true,parent:null}}),true);
});
test('drag is not an organ click',()=>{
  assert.equal(isClick({x:10,y:20},{x:100,y:20}),false);
  assert.equal(isClick({x:10,y:20},{x:12,y:22}),true);
  assert.equal(isClick(null,{x:12,y:22}),false);
});
test('drag returning to start never becomes a click',()=>{
  const start={x:10,y:20};trackMovement(start,{x:80,y:20});trackMovement(start,{x:10,y:20});
  assert.equal(isClick(start,{x:10,y:20}),false);
});
test('source mode clears old effects and system membership is not evidence',()=>{
  assert.equal(visualStyle('liver',{effects:{liver:'metabolism'}},false,0xff0000).effect,true);
  assert.equal(visualStyle('liver',{effects:{},members:['liver']},false,0xff0000).effect,false);
  assert.equal(visualStyle('liver',{effects:{}},false,0xff0000).color,0x9fb8cc);
  assert.equal(visualStyle('liver',{effects:{}},true,0xff0000).color,0xff0000);
});
