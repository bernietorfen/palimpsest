#version 430
in vec3 world_position;
in vec3 world_normal;
in vec3 local_position;
in vec2 field_uv;
out vec4 fragColor;
uniform sampler2D material_field;
uniform sampler2D shadow_key;
uniform sampler2D shadow_fill;
uniform mat4 key_projection;
uniform mat4 fill_projection;
uniform vec3 key_position;
uniform vec3 fill_position;
uniform vec3 camera;
uniform int first_wall_triangle;
uniform int diagnostic;
uniform int palette;
uniform float shadow_softness;
uniform int area_shadow;
const float PI=3.141592653589793;

vec4 fieldAt(vec2 uv) {
    ivec2 size=textureSize(material_field,0);
    vec2 pixel=fract(uv)*vec2(size);
    ivec2 cell=ivec2(floor(pixel))%size;
    ivec2 next=(cell+ivec2(1))%size;
    vec2 f=fract(pixel);
    return mix(mix(texelFetch(material_field,cell,0),
                   texelFetch(material_field,ivec2(next.x,cell.y),0),f.x),
               mix(texelFetch(material_field,ivec2(cell.x,next.y),0),
                   texelFetch(material_field,next,0),f.x),f.y);
}
vec2 disk(int i,int count) {
    float r=sqrt((float(i)+.5)/float(count));
    float a=(float(i)+.5)*2.399963229728653;
    return r*vec2(cos(a),sin(a));
}
float visibility(sampler2D map,mat4 projection,vec3 p,vec3 n,vec3 light) {
    if(diagnostic==4) return 1.;
    vec4 q=projection*vec4(p,1.);
    vec3 uvz=q.xyz/q.w*.5+.5;
    if(any(lessThan(uvz,vec3(0.))) || any(greaterThan(uvz,vec3(1.)))) return 1.;
    float nl=max(dot(n,normalize(light-p)),0.);
    float bias=.00006+.00008*sqrt(max(0.,1.-nl*nl))/max(nl,.08);
    float receiver=uvz.z-bias;
    if(area_shadow==1) {
        vec2 pixel=1./vec2(textureSize(map,0));
        vec2 coordinate=uvz.xy/pixel-.5;
        vec2 cell=floor(coordinate),fraction=fract(coordinate);
        float a=step(receiver,texture(map,(cell+vec2(.5,.5))*pixel).r);
        float b=step(receiver,texture(map,(cell+vec2(1.5,.5))*pixel).r);
        float c=step(receiver,texture(map,(cell+vec2(.5,1.5))*pixel).r);
        float d=step(receiver,texture(map,(cell+vec2(1.5,1.5))*pixel).r);
        return mix(mix(a,b,fraction.x),mix(c,d,fraction.x),fraction.y);
    }
    float blocker=0.,count=0.;
    for(int i=0;i<12;i++) {
        float depth=texture(map,uvz.xy+disk(i,12)*.022*shadow_softness).r;
        if(depth<receiver) { blocker+=depth; count+=1.; }
    }
    if(count<.5) return 1.;
    blocker/=count;
    float radius=clamp((receiver-blocker)/max(blocker,.05)*.060*shadow_softness,.00055,.025);
    float result=0.;
    for(int i=0;i<32;i++) {
        float depth=texture(map,uvz.xy+disk(i,32)*radius).r;
        result+=smoothstep(receiver-.00012,receiver+.00012,depth);
    }
    return result/32.;
}
vec3 brdf(vec3 n,vec3 v,vec3 l,vec3 base,float rough,float metal) {
    vec3 h=normalize(v+l);
    float nl=max(dot(n,l),0.),nv=max(dot(n,v),.001);
    float nh=max(dot(n,h),0.),vh=max(dot(v,h),0.);
    float a=rough*rough,a2=a*a;
    float denominator=nh*nh*(a2-1.)+1.;
    float D=a2/(PI*denominator*denominator+.00001);
    float k=(rough+1.)*(rough+1.)/8.;
    float G=nv/(nv*(1.-k)+k)*nl/(nl*(1.-k)+k);
    vec3 f0=mix(vec3(.045),base,metal);
    vec3 F=f0+(1.-f0)*pow(1.-vh,5.);
    return ((1.-F)*(1.-metal)*base/PI+D*G*F/(4.*nl*nv+.001))*nl;
}
void main() {
    vec3 n=normalize(world_normal);
    bool wall=gl_PrimitiveID>=first_wall_triangle;
    if(wall) n=normalize(cross(dFdx(world_position),dFdy(world_position)));
    if(!gl_FrontFacing) n=-n;
    vec4 f=fieldAt(field_uv);
    float history=clamp(abs(f.y)*1.5,0.,1.);
    float fatigue=clamp(f.z,0.,1.);
    float ink=smoothstep(.035,.66,abs(f.y));
    float line=.5+.5*sin(f.y*47.+f.x*16.);
    line=pow(line,18.)*smoothstep(.035,.14,abs(f.y));
    vec3 base=mix(vec3(.68,.65,.55),vec3(.025,.045,.053),ink*.91);
    base=mix(base,vec3(.43,.20,.066),line*.82);
    float rough=.68,metal=.025;
    if(palette==1) {
        base=mix(vec3(.62,.53,.34),vec3(.035,.065,.061),ink*.87);
        base=mix(base,vec3(.59,.22,.060),line*.8);
        rough=.52+.15*fatigue;
        metal=.06+line*.22;
    }
    if(palette==2) {
        base=mix(vec3(.045,.068,.072),vec3(.015,.024,.031),ink*.75);
        base=mix(base,vec3(.52,.33,.12),line*.93);
        rough=.42+.15*fatigue;
        metal=.18+line*.4;
    }
    // Fine fibres are band-limited with pixel derivatives. No texture assets.
    float fibrePhase=1200.*field_uv.x+17.*sin(53.*field_uv.y)+5.*sin(37.*field_uv.x);
    float bandwidth=fwidth(fibrePhase);
    float fibre=sin(fibrePhase)*exp(-bandwidth*bandwidth*.24);
    base*=1.+fibre*.024;
    if(wall) { base=mix(base,vec3(.35,.23,.12),.55); rough=.8; }
    vec3 v=normalize(camera-world_position);
    vec3 l1=normalize(key_position-world_position),l2=normalize(fill_position-world_position);
    float vis1=visibility(shadow_key,key_projection,world_position,n,key_position);
    float vis2=visibility(shadow_fill,fill_projection,world_position,n,fill_position);
    vec3 col=brdf(n,v,l1,base,rough,metal)*vec3(5.2,4.55,3.75)*vis1;
    col+=brdf(n,v,l2,base,rough+.08,metal)*vec3(1.0,1.65,2.0)*vis2;
    col+=base*vec3(.055,.072,.085)*(.55+.45*n.y);
    col+=base*vec3(.022,.018,.012)*(.5-.5*n.y);
    col+=vec3(.095,.056,.019)*pow(1.-max(dot(n,v),0.),4.)*(.3+.7*vis2);
    col+=line*vec3(.038,.013,.003)*history;
    if(diagnostic==1) col=.5+.5*n;
    if(diagnostic==2) col=vec3(.12+.75*max(dot(n,l1),0.)*vis1);
    if(diagnostic==3) col=vec3(vis1);
    fragColor=vec4(col,1.);
}
