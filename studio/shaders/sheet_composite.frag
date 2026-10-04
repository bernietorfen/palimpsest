#version 430
in vec2 uv;
out vec4 fragColor;
uniform sampler2D image;
uniform float sample_weight;
uniform float exposure;
uniform int backdrop;
uniform int final_pass;
void main() {
    vec4 rendered=texture(image,uv);
    vec2 p=uv-.5;
    float vignette=clamp(1.-.65*dot(p,p),.3,1.);
    vec3 background=vec3(.0013,.0021,.0028)*vignette;
    background+=vec3(.0009,.0012,.0015)*exp(-7.*length(p-vec2(.2,.15)));
    if(backdrop==1) background=vec3(.50,.45,.36)*vignette;
    vec3 color=mix(background,rendered.rgb,rendered.a);
    if(final_pass==1) {
        color=1.-exp(-max(color,vec3(0.))*exposure);
        color=pow(color,vec3(1./2.2));
    }
    fragColor=vec4(color,1.)*(final_pass==1?1.:sample_weight);
}
