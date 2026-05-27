import { tsParticles } from "@tsparticles/engine";
import { loadConfettiPreset } from "@tsparticles/preset-confetti";

(async () => {
  await loadConfettiPreset(tsParticles);

  await tsParticles.load({
    id: "tsparticles",
    options: {
      preset: "confetti",

      particles: {
        paint: {
          fill: {
            color: {
              value: ["#CB0D07", "#EBAB00", "#FCE45C", "#008484", "#405480"],
            },
          },
        },
      },

      emitters: [
        {
          startCount: 50,
          position: {
            x: 0,
            y: 60,
          },
          rate: {
            delay: 0,
            quantity: 0,
          },
          life: {
            duration: 0.1,
            count: 1,
          },
          particles: {
            move: {
              direction: "top-right",
              speed: {
                min: 50,
                max: 150,
              },
            },
          },
        },
        {
          startCount: 50,
          position: {
            x: 100,
            y: 60,
          },
          rate: {
            delay: 0,
            quantity: 0,
          },
          life: {
            duration: 0.1,
            count: 1,
          },
          particles: {
            move: {
              direction: "top-left",
              speed: {
                min: 50,
                max: 150,
              },
            },
          },
        },
      ],
    },
  });
})();
