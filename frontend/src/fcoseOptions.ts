export type FcoseLayout = {
  name: "fcose";
  quality: "proof";
  randomize: false;
  packComponents: false;
  animate: boolean;
  fit: boolean;
  padding: number;
  animationDuration?: number;
  fixedNodeConstraint?: { nodeId: string; position: { x: number; y: number } }[];
};

function base(): FcoseLayout {
  return {
    name: "fcose",
    quality: "proof",
    randomize: false,
    packComponents: false,
    animate: false,
    fit: false,
    padding: 40,
  };
}

export function seedLayout(): FcoseLayout {
  return { ...base(), fit: true };
}

export function expandLayout(): FcoseLayout {
  return { ...base(), animate: true, animationDuration: 400 };
}

export function relaxLayout(
  nodeId: string,
  position: { x: number; y: number },
): FcoseLayout {
  return {
    ...expandLayout(),
    animationDuration: 350,
    fixedNodeConstraint: [{ nodeId, position }],
  };
}
