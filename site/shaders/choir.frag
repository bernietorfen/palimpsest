#version 300 es
precision highp float;
precision highp int;
in vec3 world;
in vec3 surfaceNormal;
in vec2 chart;
uniform sampler2D fields;
uniform sampler2D shadowMap;
uniform mat4 lightProjection;
uniform vec3 eye;
uniform int kind;
uniform int pass;
uniform int bodyId;
uniform bool selected;
uniform float opening;
out vec4 color;
const float PI=3.14159265359;
vec4 field(vec2 q){
 ivec2 n=textureSize(fields,0);vec2 p=kind==1?clamp(q,vec2(0),vec2(1))*vec2(n-1):fract(q)*vec2(n),f=fract(p);ivec2 a=ivec2(floor(p)),b=kind==1?min(a+ivec2(1),n-1):(a+ivec2(1))%n;
 return mix(mix(texelFetch(fields,a,0),texelFetch(fields,ivec2(b.x,a.y),0),f.x),mix(texelFetch(fields,ivec2(a.x,b.y),0),texelFetch(fields,b,0),f.x),f.y);
}
float shadow(vec3 n,vec3 l){
 vec4 q0=lightProjection*vec4(world,1);vec3 q=q0.xyz/q0.w*.5+.5;if(any(lessThan(q,vec3(0)))||any(greaterThan(q,vec3(1))))return 1.0;
 float sum=0.0,bias=.00015+.0003*(1.0-abs(dot(n,l)));vec2 pixel=1.0/vec2(textureSize(shadowMap,0));
 for(int y=-2;y<=2;y++)for(int x=-2;x<=2;x++)sum+=q.z-bias<=texture(shadowMap,q.xy+vec2(x,y)*pixel*1.4).r?1.0:0.0;
 return sum/25.0;
}
vec3 brdf(vec3 n,vec3 v,vec3 l,vec3 base,float rough,float metal){
 vec3 h=normalize(v+l);float nl=max(dot(n,l),0.0),nv=max(dot(n,v),.001),nh=max(dot(n,h),0.0),vh=max(dot(v,h),0.0);
 float a=rough*rough,a2=a*a,d=nh*nh*(a2-1.0)+1.0,D=a2/(PI*d*d+.00001),k=(rough+1.0)*(rough+1.0)/8.0,G=nv/(nv*(1.0-k)+k)*nl/(nl*(1.0-k)+k);
 vec3 f0=mix(vec3(.045),base,metal),F=f0+(1.0-f0)*pow(1.0-vh,5.0);return ((1.0-F)*(1.0-metal)*base/PI+D*G*F/(4.0*nl*nv+.001))*nl;
}
void main(){
 vec4 f=field(chart);float s=chart.x,phi=(chart.y-.5)*2.0*PI;
 if(kind==0&&s>=.065&&s<=.955&&abs(phi)<=PI*opening*.975&&2.4*f.z>(.90+.30*sin(5.0*phi+4.0*s)+.15*cos(3.0*phi-6.0*s)))discard;
 if(pass==1){color=vec4(1);return;}
 if(pass==2){color=kind==0?vec4(float(bodyId+1)/255.0,chart,1):vec4(0,0,0,1);return;}
 vec3 n=normalize(surfaceNormal)*(gl_FrontFacing?1.0:-1.0),v=normalize(eye-world),l=normalize(vec3(-8,12,9)-world),fill=normalize(vec3(7,7,-7)-world);float visibility=shadow(n,l);
 if(kind==2){vec3 paper=vec3(1.9,1.77,1.58)*(.36+.64*visibility);color=vec4(pow(paper/(paper+vec3(.65)),vec3(1.0/2.2)),1);return;}
 float ink=smoothstep(.015,.34,abs(f.y)),line=pow(.5+.5*sin(f.y*61.0+f.x*8.0),18.0)*smoothstep(.012,.10,abs(f.y));
 vec3 pigment=mix(vec3(.36,.047,.015),vec3(.014,.071,.115),smoothstep(-.025,.025,f.y));vec3 base=mix(vec3(.76,.72,.63),pigment,ink*.95);base=mix(base,vec3(.52,.26,.07),line*.75);float rough=.56+.14*clamp(f.z,0.0,1.0),metal=.025;
 if(kind==1){base=mix(vec3(.025,.076,.085),vec3(.62,.28,.046),clamp(sqrt(max(f.z,0.0))*.85,0.0,1.0));rough=.32;metal=.3;}
 vec3 lit=brdf(n,v,l,base,rough,metal)*vec3(4.8,4.2,3.4)*visibility+brdf(n,v,fill,base,rough,metal)*vec3(1.1,1.5,1.8);
 lit+=base*(vec3(.15,.18,.20)+vec3(.10,.085,.065)*max(n.y,0.0));lit+=vec3(.36,.29,.18)*pow(1.0-abs(dot(n,v)),3.0)*.15;
 lit+=base*vec3(.24,.18,.10)*max(-dot(n,l),0.0)*visibility*(1.0-ink*.6);
 if(selected&&kind==0)lit+=vec3(.07,.025,.003)*pow(1.0-abs(dot(n,v)),4.0);
 color=vec4(pow(lit/(lit+vec3(.65)),vec3(1.0/2.2)),1);
}
