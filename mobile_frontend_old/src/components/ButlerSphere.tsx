import React, { useEffect, useRef } from 'react';
import { View } from 'react-native';
import { GLView } from 'expo-gl';
import { Renderer } from 'expo-three';
import * as THREE from 'three';

export const ButlerSphere: React.FC = () => {
  const animRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (animRef.current != null) {
        cancelAnimationFrame(animRef.current);
      }
    };
  }, []);

  return (
    <View style={{ flex: 1, borderRadius: 24, overflow: 'hidden', backgroundColor: '#020617' }}>
      <GLView
        style={{ flex: 1 }}
        onContextCreate={async (gl) => {
          const { drawingBufferWidth: width, drawingBufferHeight: height } = gl;

          const scene = new THREE.Scene();
          scene.background = new THREE.Color('#020617');

          const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
          camera.position.z = 3;

          const renderer = new Renderer({ gl });
          renderer.setSize(width, height);

          const geometry = new THREE.SphereGeometry(1, 64, 64);
          const material = new THREE.MeshStandardMaterial({
            color: new THREE.Color('#22d3ee'),
            metalness: 0.9,
            roughness: 0.2,
          });
          const sphere = new THREE.Mesh(geometry, material);
          scene.add(sphere);

          const light = new THREE.DirectionalLight('#38bdf8', 1.2);
          light.position.set(5, 5, 5);
          scene.add(light);
          scene.add(new THREE.AmbientLight('#0ea5e9', 0.3));

          const clock = new THREE.Clock();

          const renderLoop = () => {
            const t = clock.getElapsedTime();
            sphere.rotation.y += 0.003;
            sphere.rotation.x = Math.sin(t * 0.5) * 0.15;
            const intensity = 0.5 + 0.5 * Math.sin(t * 1.2);
            material.emissive = new THREE.Color('#0ea5e9').multiplyScalar(intensity);

            renderer.render(scene, camera);
            gl.endFrameEXP();

            animRef.current = requestAnimationFrame(renderLoop);
          };

          renderLoop();
        }}
      />
    </View>
  );
};
