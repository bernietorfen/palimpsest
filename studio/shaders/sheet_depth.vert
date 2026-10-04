#version 430
in vec3 position;
uniform mat4 model;
uniform mat4 light_projection;
void main() { gl_Position=light_projection*model*vec4(position,1.); }
