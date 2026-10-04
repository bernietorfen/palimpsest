/**
 * A finite unitary clock and selected complex coherence observations.
 *
 * This core evaluates the declared pure-state family with fixed, known
 * populations. Its readings are calculated ensemble expectations. Selecting
 * observations does not change the state or model measurement backaction.
 * Graph gaps come from the independently verified scientific record.
 */

const finite = (value, label) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${label} must be a finite number`);
  }
  return value;
};

const freezeVector = values => Object.freeze(Array.from(values));

function componentsFor(size, edges, emphasis) {
  const neighbors = Array.from({ length: size }, () => []);
  edges.forEach(([first, second], index) => {
    if (emphasis[index] > 0) {
      neighbors[first].push(second);
      neighbors[second].push(first);
    }
  });
  const visited = new Set();
  let components = 0;
  for (let start = 0; start < size; start += 1) {
    if (visited.has(start)) continue;
    components += 1;
    const pending = [start];
    while (pending.length) {
      const node = pending.pop();
      if (visited.has(node)) continue;
      visited.add(node);
      pending.push(...neighbors[node]);
    }
  }
  return components;
}

function prepareGraph(specification, size, id) {
  let edges;
  let emphasis;
  if (specification.kind === 'complete') {
    edges = [];
    for (let first = 0; first < size; first += 1) {
      for (let second = first + 1; second < size; second += 1) edges.push([first, second]);
    }
    emphasis = edges.map(() => 1);
  } else if (specification.kind === 'edges') {
    if (!Array.isArray(specification.edges) || !Array.isArray(specification.emphasis)) {
      throw new TypeError('An observation graph needs edges and their emphases');
    }
    edges = specification.edges.map(edge => Array.from(edge));
    emphasis = Array.from(specification.emphasis);
  } else {
    throw new TypeError('Unknown observation graph representation');
  }
  if (edges.length !== emphasis.length) throw new RangeError('Each edge needs one emphasis');
  const seen = new Set();
  edges.forEach((edge, index) => {
    const [first, second] = edge;
    if (edge.length !== 2 || !Number.isInteger(first) || !Number.isInteger(second)
        || first < 0 || second >= size || first >= second) {
      throw new RangeError('Observation edges must be ordered, distinct valid level indices');
    }
    const key = `${first}:${second}`;
    if (seen.has(key)) throw new RangeError('Repeated observation edges are not admitted');
    seen.add(key);
    if (finite(emphasis[index], 'Edge emphasis') < 0) throw new RangeError('Edge emphasis cannot be negative');
  });
  const components = componentsFor(size, edges, emphasis);
  const gap = finite(specification.spectralGap, 'Stored graph spectral gap');
  if (components !== specification.components || gap < 0 || (components === 1) !== (gap > 0)) {
    throw new RangeError('Stored graph gap and connectivity metadata disagree');
  }
  return Object.freeze({
    id,
    edges: Object.freeze(edges.map(freezeVector)),
    emphasis: freezeVector(emphasis),
    components,
    spectralGap: gap,
  });
}

export function createRelationalClock(specification) {
  if (!specification || !Array.isArray(specification.energies) || !Array.isArray(specification.populations)) {
    throw new TypeError('The clock needs energy and population vectors');
  }
  const energies = specification.energies.map(value => finite(value, 'Energy'));
  const populations = specification.populations.map(value => finite(value, 'Population'));
  const size = energies.length;
  if (size < 2 || populations.length !== size || populations.some(value => value <= 0)
      || Math.abs(populations.reduce((total, value) => total + value, 0) - 1) > 1e-14) {
    throw new RangeError('Populations must be positive, normalized and match the clock dimension');
  }
  const roots = populations.map(Math.sqrt);
  const graphs = Object.freeze(Object.fromEntries(
    Object.entries(specification.graphs).map(([id, graph]) => [id, prepareGraph(graph, size, id)]),
  ));
  const parameters = Object.freeze({
    id: specification.id,
    size,
    energies: freezeVector(energies),
    populations: freezeVector(populations),
  });
  const states = new WeakSet();

  function requireState(current) {
    if (!states.has(current)) throw new TypeError('Use a state created by this clock');
  }

  function requireGraph(id) {
    const graph = Object.hasOwn(graphs, id) ? graphs[id] : null;
    if (!graph) throw new RangeError('Unknown observation graph');
    return graph;
  }

  function state(time) {
    finite(time, 'Time');
    const real = new Array(size);
    const imaginary = new Array(size);
    for (let index = 0; index < size; index += 1) {
      const phase = energies[index] * time;
      if (!Number.isFinite(phase)) throw new RangeError('Time exceeds the finite numerical phase range');
      real[index] = roots[index] * Math.cos(phase);
      imaginary[index] = -roots[index] * Math.sin(phase);
    }
    const current = Object.freeze({ time, real: freezeVector(real), imaginary: freezeVector(imaginary) });
    states.add(current);
    return current;
  }

  function distanceSquared(current) {
    requireState(current);
    let meanReal = 0;
    let meanImaginary = 0;
    for (let index = 0; index < size; index += 1) {
      meanReal += roots[index] * current.real[index];
      meanImaginary += roots[index] * current.imaginary[index];
    }
    let variance = 0;
    for (let index = 0; index < size; index += 1) {
      const differenceReal = current.real[index] / roots[index] - meanReal;
      const differenceImaginary = current.imaginary[index] / roots[index] - meanImaginary;
      variance += populations[index] * (differenceReal ** 2 + differenceImaginary ** 2);
    }
    return Math.min(1, Math.max(0, variance));
  }

  function distance(current) {
    return Math.sqrt(distanceSquared(current));
  }

  function coherence(current, first, second) {
    requireState(current);
    if (!Number.isInteger(first) || !Number.isInteger(second)
        || first < 0 || second < 0 || first >= size || second >= size) {
      throw new RangeError('A coherence needs two valid level indices');
    }
    return Object.freeze({
      real: current.real[first] * current.real[second] + current.imaginary[first] * current.imaginary[second],
      imaginary: current.imaginary[first] * current.real[second] - current.real[first] * current.imaginary[second],
    });
  }

  function graphR(current, id) {
    requireState(current);
    const graph = requireGraph(id);
    let discrepancy = 0;
    graph.edges.forEach(([first, second], index) => {
      const real = current.real[first] * current.real[second]
        + current.imaginary[first] * current.imaginary[second]
        - Math.sqrt(populations[first] * populations[second]);
      const imaginary = current.imaginary[first] * current.real[second] - current.real[first] * current.imaginary[second];
      discrepancy += graph.emphasis[index] * (real ** 2 + imaginary ** 2);
    });
    return discrepancy;
  }

  function certificate(id, measuredR, errorNorm = 0) {
    const graph = requireGraph(id);
    if (finite(measuredR, 'Measured discrepancy') < 0 || finite(errorNorm, 'Observation error norm') < 0) {
      throw new RangeError('Discrepancy and the deterministic observation error bound cannot be negative');
    }
    const available = graph.components === 1;
    return Object.freeze({
      available,
      upperBound: available
        ? Math.min(1, (Math.sqrt(measuredR) + errorNorm) / Math.sqrt(graph.spectralGap))
        : null,
      spectralGap: graph.spectralGap,
      measuredR,
      errorNorm,
      scope: 'Known fixed-population pure states; deterministic weighted complex-coherence error bound.',
    });
  }

  function measure(current, id, errorNorm = 0) {
    const discrepancy = graphR(current, id);
    const squaredDistance = distanceSquared(current);
    return Object.freeze({
      time: current.time,
      graph: id,
      distance: Math.sqrt(squaredDistance),
      squaredDistance,
      discrepancy,
      certificate: certificate(id, discrepancy, errorNorm),
    });
  }

  return Object.freeze({ parameters, graphs, state, distance, distanceSquared, coherence, graphR, certificate, measure });
}
