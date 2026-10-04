#version 300 es
precision highp float;
precision highp int;
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec2 coordinate;
uniform sampler2D fields;
uniform mat4 model;
uniform mat4 viewProjection;
uniform vec4 shape; // opening, flare, height, pleats
uniform vec3 shape2; // twist, thickness, deformation
uniform int kind;
out vec3 world;
out vec3 surfaceNormal;
out vec2 chart;
const float PI=3.14159265359;
vec4 field(vec2 q){
 vec2 p=fract(q)*vec2(textureSize(fields,0)),f=fract(p);ivec2 n=textureSize(fields,0),a=ivec2(floor(p))%n,b=(a+ivec2(1))%n;
 return mix(mix(texelFetch(fields,a,0),texelFetch(fields,ivec2(b.x,a.y),0),f.x),mix(texelFetch(fields,ivec2(a.x,b.y),0),texelFetch(fields,b,0),f.x),f.y);
}
vec3 listener(vec2 q){
 float s=q.x,phi=(q.y-.5)*2.0*PI*shape.x;vec4 f=field(vec2(s,phi/(2.0*PI)+.5));float moving=tanh(f.x*1.8),memory=tanh(f.y*2.3);
 float pleat=(.045+.12*pow(max(s,0.0),1.5))*sin(shape.w*phi+1.6*s);
 float radius=(.25+1.10*s+.34*s*s+pleat)*shape.y+shape2.z*(.18+.82*s)*(.23*moving+.27*memory);
 float theta=phi+shape2.x*s+shape2.z*.24*s*memory;
 float y=(-.96+2.02*s-.24*s*s)*shape.z+.19*s*s*sin(3.0*phi+.6)+shape2.z*s*(.18*moving+.12*memory);
 return vec3(radius*cos(theta),y,radius*sin(theta));
}
void main(){
 vec3 p=position,n=normal;chart=coordinate;
 if(kind==0){p=listener(coordinate);n=normalize(cross(listener(coordinate+vec2(.0004,0))-listener(coordinate-vec2(.0004,0)),listener(coordinate+vec2(0,.0004))-listener(coordinate-vec2(0,.0004))));p+=n*shape2.y;chart=vec2(coordinate.x,(coordinate.y-.5)*shape.x+.5);}
 world=(model*vec4(p,1)).xyz;surfaceNormal=normalize(mat3(model)*n);gl_Position=viewProjection*vec4(world,1);
}
