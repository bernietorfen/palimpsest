#version 430
in vec3 position;
in vec3 normal;
in vec2 chart;
uniform mat4 model;
uniform mat4 view_projection;
out vec3 world_position;
out vec3 world_normal;
out vec3 local_position;
out vec2 field_uv;
void main() {
    world_position=(model*vec4(position,1.)).xyz;
    world_normal=mat3(model)*normal;
    local_position=position;
    field_uv=chart;
    gl_Position=view_projection*vec4(world_position,1.);
}
