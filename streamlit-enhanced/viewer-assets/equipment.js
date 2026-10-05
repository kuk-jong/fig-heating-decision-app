export function addEquipment(THREE,group,s,{equipment=true,curtain='open'}={}){
 const W=s.width*s.spans,L=s.length,scale=Math.min(1,W/7,s.side/2.5,L/8);
 const mat=(c)=>new THREE.MeshStandardMaterial({color:c,roughness:.55});
 const blue=mat(0x397eac),dark=mat(0x3c555f),white=mat(0xdfe8e8),red=mat(0xb17d69),green=mat(0x699487),pipe=mat(0x498bb0);
 function label(text,x,y,z,parent){const canvas=document.createElement('canvas');canvas.width=512;canvas.height=96;const ctx=canvas.getContext('2d');ctx.fillStyle='#173745';ctx.fillRect(0,0,512,96);ctx.fillStyle='#fff';ctx.font='bold 32px sans-serif';ctx.textAlign='center';ctx.fillText(text,256,60);const texture=new THREE.CanvasTexture(canvas);const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false}));sprite.position.set(x,y,z);sprite.scale.set(1.65,.31,1);parent.add(sprite)}
 if(equipment){const rack=new THREE.Group();rack.name='fertigation-equipment';rack.scale.setScalar(scale);rack.position.set(0,0,-L/2+1.2*scale);group.add(rack);
 function box(w,h,d,x,y,z,m){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m);mesh.position.set(x,y,z);rack.add(mesh);return mesh}
 function cylinder(r,h,x,z,m){const mesh=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,24),m);mesh.position.set(x,h/2,z);rack.add(mesh);const lid=new THREE.Mesh(new THREE.CylinderGeometry(r*.92,r*.92,.08,24),dark);lid.position.set(x,h+.04,z);rack.add(lid);return h}
 cylinder(.62,1.65,-2.2,0,blue);label('원수탱크',-2.2,2.05,0,rack);
 cylinder(.43,1.18,1.05,0,red);label('양액 A',1.05,1.6,0,rack);cylinder(.43,1.18,2.25,0,green);label('양액 B',2.25,1.6,0,rack);
 box(.85,1.4,.55,-.55,.78,0,white);box(.63,.42,.03,-.55,1.08,.29,dark);box(.45,.25,.03,-.55,1.08,.31,blue);for(let i=0;i<3;i++)box(.11,.55,.14,-.82+i*.25,.42,.33,pipe);label('양액기 1대',-.55,1.85,0,rack);
 function line(points){const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));rack.add(new THREE.Mesh(new THREE.TubeGeometry(curve,24,.045,8,false),pipe))}
 line([[-2.2,.25,.4],[-2.2,.25,.7],[-.55,.25,.7],[-.55,.5,.34]]);line([[1.05,.2,.3],[1.05,.2,.8],[-.2,.2,.8],[-.2,.45,.34]]);line([[2.25,.2,.3],[2.25,.2,1],[-.1,.2,1],[-.1,.4,.34]]);
 }
 if(curtain!=='hidden'){const fabric=new THREE.MeshStandardMaterial({color:0xd9cfb2,side:THREE.DoubleSide,roughness:1});const y=s.side+.12;for(let q=0;q<s.spans;q++){const x=-W/2+(q+.5)*s.width;const depth=curtain==='closed'?L:Math.min(1.2,L*.12);const mesh=new THREE.Mesh(new THREE.PlaneGeometry(s.width-.1,depth),fabric);mesh.rotation.x=-Math.PI/2;mesh.position.set(x,y,curtain==='closed'?0:-L/2+depth/2);mesh.name='thermal-curtain';group.add(mesh);if(curtain==='open'){for(let j=0;j<8;j++){const fold=new THREE.Mesh(new THREE.BoxGeometry(s.width-.1,.045,depth/16),fabric);fold.position.set(x,y+.03,-L/2+depth*j/8);group.add(fold)}}}label(curtain==='closed'?'보온커튼 · 닫힘':'보온커튼 · 접힘',0,y+.5,-L/2+.7,group)}
}
