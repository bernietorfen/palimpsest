#version 430
// PALIMPSEST, study renderer. Geometry and material are authored for this work.
in vec2 uv;
out vec4 fragColor;
uniform sampler2D material_field;
uniform vec2 resolution;
uniform float time;
uniform float memory_gain;
uniform float aperture;
uniform float turn;
uniform int design;
uniform vec3 camera;
uniform vec3 target;
uniform vec2 jitter;
uniform float sample_weight;
uniform int diagnostic;
uniform int style;
uniform float light_angle;
uniform float exposure;
uniform float focal_length;
uniform float focus_distance;
uniform float lens_radius;
uniform vec2 lens_sample;
uniform float camera_roll;
uniform int shadow_mode;
uniform int sample_index;
uniform float march_scale;
uniform float normal_step;
const float PI = 3.141592653589793;

mat2 rotate(float a) { float s=sin(a), c=cos(a); return mat2(c,-s,s,c); }
float grain(vec3 p) {
    p = fract(p * vec3(.10317,.10731,.09729));
    p += dot(p, p.yzx + 23.27);
    return fract((p.x+p.y)*p.z);
}
vec3 localPoint(vec3 p) {
    p.xz = rotate(turn) * p.xz;
    p.xy = rotate(-.31) * p.xy;
    p.yz = rotate(.18) * p.yz;
    return p;
}
vec4 fieldAt(float theta, float phi) {
    // Hardware linear-filter fractions can be too coarse for tiny normal
    // differences. Interpolate fetched texels in full shader float precision.
    ivec2 size=textureSize(material_field,0);
    vec2 pixel=fract(vec2(theta,phi)/(2.*PI)+.5)*vec2(size);
    ivec2 cell=(ivec2(floor(pixel))+size)%size;
    ivec2 next=(cell+ivec2(1))%size;
    vec2 a=fract(pixel);
    vec4 lo=mix(texelFetch(material_field,cell,0),
                texelFetch(material_field,ivec2(next.x,cell.y),0),a.x);
    vec4 hi=mix(texelFetch(material_field,ivec2(cell.x,next.y),0),
                texelFetch(material_field,next,0),a.x);
    return mix(lo,hi,a.y);
}

// An open, twice-rolled sheet. Each angular branch is a different part of one
// continuous chart, so the inner and outer leaves do not repeat the same ink.
float folioAt(vec3 p, out vec2 coordinates) {
    float theta=p.x*(2.*PI/2.8);
    vec2 center=vec2(.22*sin(1.8*p.x),.13*sin(2.2*p.x+.4));
    vec2 section=p.yz-center;
    float angle=atan(section.x,section.y);
    float best=100.;
    coordinates=vec2(0.);
    for(int winding=-1;winding<=2;winding++) {
        float phi=angle+float(winding)*2.*PI;
        vec4 f=fieldAt(theta,phi*.5);
        float radius=.55+.072*phi;
        radius+=.048*sin(3.*phi+theta)+.038*cos(4.*theta+phi);
        radius+=memory_gain*(.085*tanh(f.x*1.6)+.13*tanh(f.y*2.1));
        float d=abs(length(section)-radius)-.013;
        float edge=abs(p.x)-(1.34+.055*sin(2.*phi));
        d=max(d,edge);
        float window=(f.z-.56-.30*sin(2.*theta+4.*phi)-.16*cos(5.*theta-phi))*.065;
        d=max(d,window);
        // Close each chart end with a physical rim, instead of a discontinuous
        // branch disappearance at the angular seam.
        d=max(d,(-PI-phi)*.05);
        d=max(d,(phi-3.*PI)*.05);
        if(d<best) { best=d; coordinates=vec2(theta,phi*.5); }
    }
    return best;
}

// A thin, asymmetrically folded toroidal sheet. Its rest geometry, memory
// embossing, fatigue apertures, and moving relief are separate visible layers.
float surface(vec3 world) {
    vec3 p = localPoint(world);
    if (design == 4) {
        vec2 coordinates;
        return folioAt(p,coordinates)*.20;
    }
    float theta = atan(p.z,p.x);
    float major = 1.03 + .13*cos(3.*theta+.4) + .09*sin(2.*theta-1.);
    float lift = .18*sin(2.*theta+.3) + .075*cos(5.*theta);
    vec2 crossSection = vec2(length(p.xz)-major, p.y-lift);
    float phi = atan(crossSection.y,crossSection.x);
    vec4 f = fieldAt(theta,phi);
    float fold = .055*cos(7.*theta + 2.*phi + 2.7*f.y);
    fold += .028*sin(13.*theta-3.*phi+1.5*f.x);
    float radius = .30 + .072*cos(2.*phi+theta) + .046*sin(3.*theta-.4);
    radius += fold + memory_gain*(.11*tanh(f.x*1.6)+.19*tanh(f.y*2.1));
    float thickness = .014 + .009*(.5+.5*cos(3.*phi-theta));
    float d = abs(length(crossSection)-radius) - thickness;
    float slit = sin(3.*phi + 1.7*sin(2.*theta) + 1.8*f.y);
    float opening = aperture + .7*f.z;
    float tear = (.16 + opening - slit) * .055;
    if (design == 3) {
        // An unwritten skin is intact. Fatigue opens windows that remain after
        // the rest-shape inscription fades: forgetting cannot undo the wear.
        tear = (-1.24 + 2.02*f.z + aperture - slit) * .055;
    }
    d = max(d,tear);
    if (design == 1) {
        // A break exposes the material's otherwise hidden inner face.
        d = max(d, .06 - abs(theta+.24));
    }
    if (design == 2) {
        d = max(d, (.3 + .45*cos(5.*theta+f.y*3.) - cos(phi))*.06);
    }
    return d*.20;
}
vec4 surfaceField(vec3 world) {
    vec3 p = localPoint(world);
    if (design == 4) {
        vec2 coordinates;
        folioAt(p,coordinates);
        return fieldAt(coordinates.x,coordinates.y);
    }
    float theta = atan(p.z,p.x);
    float major = 1.03+.13*cos(3.*theta+.4)+.09*sin(2.*theta-1.);
    float lift = .18*sin(2.*theta+.3)+.075*cos(5.*theta);
    return fieldAt(theta,atan(p.y-lift,length(p.xz)-major));
}
vec3 normalAt(vec3 p) {
    float e=normal_step;
    vec2 h=vec2(e,0);
    return normalize(vec3(surface(p+h.xyy)-surface(p-h.xyy),
                          surface(p+h.yxy)-surface(p-h.yxy),
                          surface(p+h.yyx)-surface(p-h.yyx)));
}
float visibility(vec3 p, vec3 dir, float maxDist) {
    if (shadow_mode == 0) return 1.;
    if (shadow_mode == 2) {
        float t=.004;
        for(int i=0;i<440;i++) {
            vec3 point=p+dir*t;
            if(t>maxDist || length(point)>2.41) return 1.;
            float distance=surface(point);
            if(distance<.00008) return 0.;
            t+=max(distance*march_scale,.00012);
        }
        return 1.;
    }
    float t=.008, result=1.;
    for(int i=0;i<52;i++) {
        float h=surface(p+dir*t);
        result=min(result,18.*h/t);
        t+=clamp(h,.006,.13);
        if(result<.012 || t>maxDist) break;
    }
    return clamp(result,0.,1.);
}
float occlusion(vec3 p,vec3 n) {
    float total=0., weight=1.;
    for(int i=1;i<=6;i++) {
        float h=.018+float(i)*.034;
        total+=(h*.20-surface(p+n*h))*weight;
        weight*=.65;
    }
    return clamp(1.-total*3.2,.2,1.);
}
vec3 brdf(vec3 n,vec3 v,vec3 l,vec3 albedo,float rough,float metal) {
    vec3 h=normalize(v+l);
    float nl=max(dot(n,l),0.), nv=max(dot(n,v),.001);
    float nh=max(dot(n,h),0.), vh=max(dot(v,h),0.);
    float a=rough*rough, a2=a*a;
    float denom=nh*nh*(a2-1.)+1.;
    float D=a2/(PI*denom*denom+.00001);
    float k=(rough+1.)*(rough+1.)/8.;
    float G=(nv/(nv*(1.-k)+k))*(nl/(nl*(1.-k)+k));
    vec3 f0=mix(vec3(.045),albedo,metal);
    vec3 F=f0+(1.-f0)*pow(1.-vh,5.);
    vec3 spec=D*G*F/(4.*nl*nv+.001);
    return ((1.-F)*(1.-metal)*albedo/PI+spec)*nl;
}
vec3 shade(vec3 p, vec3 rd, vec3 n) {
    vec4 f=surfaceField(p);
    float history=clamp(abs(f.y)*1.5,0.,1.);
    float fatigue=clamp(f.z,0.,1.);
    float veins=.5+.5*sin(f.y*47.+f.x*16.);
    veins=pow(veins,18.)*smoothstep(.035,.14,abs(f.y));
    vec3 ivory=vec3(.73,.67,.53);
    vec3 copper=vec3(.48,.19,.083);
    vec3 ink=vec3(.044,.068,.069);
    vec3 base=mix(ivory,copper,history*.8);
    base=mix(base,ink,fatigue*.73);
    base=mix(base,vec3(.63,.34,.14),veins*.58);
    vec3 lp=localPoint(p);
    float fine=.5+.5*sin(440.*lp.x+17.*sin(31.*lp.z)+9.*sin(42.*lp.y));
    base*=.965+.035*fine;
    float rough=.46+.15*fatigue-.065*history;
    float metal=.045+.58*history;
    if (style == 1 || style == 3) {
        // Pale vellum, with memory carrying the ink and fatigue staining it.
        base=mix(vec3(.72,.66,.49),vec3(.030,.059,.062),history*.86);
        base=mix(base,vec3(.28,.085,.037),fatigue*.48);
        base=mix(base,vec3(.60,.27,.080),veins*.79);
        rough=.62+.14*fatigue;
        metal=.025+.17*veins;
        if (style == 3) {
            base=mix(vec3(.63,.60,.51),vec3(.028,.042,.050),smoothstep(.08,.70,abs(f.y))*.85);
            base=mix(base,vec3(.36,.14,.047),veins*.8);
            rough=.72;
            metal=.025;
        }
    } else if (style == 2) {
        // A dark engraved body. Color follows the same material state.
        base=mix(vec3(.032,.047,.046),vec3(.22,.067,.025),history*.8);
        base=mix(base,vec3(.48,.24,.065),veins*.84);
        rough=.32+.26*fatigue;
        metal=.35+.35*history;
    }
    vec3 v=-rd;
    if (diagnostic == 1) return .5+.5*n;
    if (diagnostic == 2) return vec3(.55)*(.13+.87*max(dot(n,normalize(vec3(-2.,4.,3.))),0.));
    float ao=occlusion(p,n);
    vec3 light1=vec3(-3.5,5.,4.5);
    vec3 light2=vec3(4.,1.6,-2.8);
    light1.xz=rotate(light_angle)*light1.xz;
    light2.xz=rotate(light_angle)*light2.xz;
    if (shadow_mode == 2) {
        vec3 seed=vec3(gl_FragCoord.xy,float(sample_index)*19.17);
        light1.xz+=(vec2(grain(seed),grain(seed+7.3))-.5)*2.3;
        light2.yz+=(vec2(grain(seed+13.1),grain(seed+23.7))-.5)*1.8;
    }
    vec3 l1=normalize(light1-p),l2=normalize(light2-p);
    float vis1=visibility(p+n*.008,l1,length(light1-p));
    float vis2=visibility(p+n*.008,l2,length(light2-p));
    vec3 col=brdf(n,v,l1,base,rough,metal)*vec3(5.2,4.4,3.5)*vis1;
    col+=brdf(n,v,l2,base,rough+.1,metal)*vec3(1.15,1.85,2.2)*vis2;
    col+=base*vec3(.17,.19,.19)*ao*(.5+.5*n.y);
    // A thin-sheet transmission approximation, explicitly an artistic shader.
    float back=pow(max(dot(-n,l1),0.),1.7);
    col+=vec3(.22,.085,.025)*back*.4*ao;
    if (style == 1) col+=vec3(.44,.23,.065)*back*.6*ao*(1.-fatigue*.55);
    float edge=pow(1.-max(dot(n,v),0.),3.);
    col+=vec3(.13,.16,.15)*edge*ao;
    col+=veins*vec3(.18,.072,.018)*history;
    return col;
}
void main() {
    vec2 coord=(gl_FragCoord.xy+jitter-.5*resolution)/resolution.y;
    vec3 forward=normalize(target-camera);
    vec3 right=normalize(cross(forward,vec3(0,1,0)));
    vec3 up=cross(right,forward);
    vec2 rolled=rotate(camera_roll)*coord;
    vec3 rd=normalize(forward*focal_length+rolled.x*right+rolled.y*up);
    vec3 focus_point=camera+rd*(focus_distance/dot(rd,forward));
    vec3 ro=camera+lens_radius*(lens_sample.x*right+lens_sample.y*up);
    rd=normalize(focus_point-ro);
    // Bound includes all extrema of the authored rest geometry and tanh relief.
    float b=dot(ro,rd), c=dot(ro,ro)-2.40*2.40;
    float discriminant=b*b-c;
    float t=discriminant>0.?max(0.,-b-sqrt(discriminant)):20.;
    float stop=discriminant>0.?-b+sqrt(discriminant):0.;
    bool hit=false;
    float previous=t;
    for(int i=0;i<1400;i++) {
        if(t>stop) break;
        float d=surface(ro+rd*t);
        if(d<.00010) {
            hit=true;
            if(d<0.) {
                float lo=previous,hi=t;
                for(int j=0;j<7;j++) {
                    float mid=(lo+hi)*.5;
                    if(surface(ro+rd*mid)>0.) lo=mid; else hi=mid;
                }
                t=(lo+hi)*.5;
            }
            break;
        }
        previous=t;
        t+=max(d,.00008)*march_scale;
    }
    float vignette=clamp(1.-.28*dot(coord,coord),.3,1.);
    vec3 color=vec3(.0012,.0020,.0027)*(1.+.4*uv.y)*vignette;
    color+=vec3(.0012,.0014,.0012)*exp(-4.*length(coord-vec2(.35,.2)));
    if (style == 1) {
        color=vec3(.50,.44,.34)*(.87+.13*uv.y)*vignette;
    }
    if(hit) {
        vec3 p=ro+rd*t;
        color=shade(p,rd,normalAt(p));
    }
    color=1.-exp(-color*exposure);
    color=pow(max(color,vec3(0)),vec3(1./2.2));
    color+=(grain(vec3(gl_FragCoord.xy,19.))-.5)/500.;
    fragColor=vec4(clamp(color,0.,1.),1.)*sample_weight;
}
