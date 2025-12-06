uniform float uTime;
uniform float uAnimation;
uniform float uOffsets[7];
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform float uInputVolume;
uniform float uOutputVolume;
uniform sampler2D uPerlinTexture;
varying vec2 vUv;

const float PI = 3.14159265358979323846;

vec2 hash2(vec2 p) {
    p = vec2(
        dot(p, vec2(127.1, 311.7)),
        dot(p, vec2(269.5, 183.3))
    );
    return fract(sin(p) * 43758.5453);
}

float noise2D(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);

    return mix(
        mix(dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
            dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
        mix(dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
            dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x),
        u.y
    );
    return 0.5 + 0.5 * noise2D(p);
}

float smoothRing(vec2 uv, float time) {
    float angle = atan(uv.y, uv.x);
    if (angle < 0.0) angle += 2.0 * PI;
    
    vec2 noiseCoord = vec2(angle / (2.0 * PI), time * 0.1);
    noiseCoord *= 6.0;
    
    float noise = noise2D(noiseCoord);
    noise = (noise - 0.5) * 8.0;
    
    float ringStart = 0.9;
    float ringWidth = 0.3;
    
    return ringStart + noise * ringWidth;
}

float flow(float radius, float theta, float offset) {
    return texture(
        uPerlinTexture, 
        vec2(radius * 0.03, theta / 4.0 / PI + offset) 
        + vec2(uAnimation * -0.2, 0.0)
    ).r;
}

void main() {
    vec2 uv = vUv * 2.0 - 1.0;
    float radius = length(uv);
    float theta = atan(uv.y, uv.x);
    if (theta < 0.0) theta += 2.0 * PI;

    float ringRadius = smoothRing(uv, uTime);
    float ringDist = abs(radius - ringRadius);
    float ringAlpha = smoothstep(0.15, 0.0, ringDist);

    float flowNoise = flow(radius, theta, uAnimation);
    vec3 color = mix(uColor1, uColor2, flowNoise);

    float volumeEffect = mix(uInputVolume, uOutputVolume, 0.5);
    float glow = 1.0 + volumeEffect * 0.5;
    color *= glow;

    float alpha = ringAlpha * (0.8 + volumeEffect * 0.2);
    alpha *= smoothstep(1.2, 0.8, radius);

    gl_FragColor = vec4(color, alpha);
}
