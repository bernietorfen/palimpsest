/** Run on the remote computation host: generate a fixture, then test the browser core. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const projectRoot = fileURLToPath(new URL('../../', import.meta.url));
const fixtureUrl = new URL('../../site/assets/data/relational-clock.json', import.meta.url);
const coreUrl = new URL('../../site/assets/relational-clock-core.js', import.meta.url);

if (process.argv.includes('--write-fixture')) {
  const python = process.env.PALIMPSEST_PYTHON || 'python';
  const producer = String.raw`
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
from studio.relational_clock import (bridge_observer, complete_observer, four_level_clock,
    group_observer, thirty_two_level_clock)

record = Path('artifacts/studies/relational-clock-001')
report = json.loads((record/'report.json').read_text())
assert report['all_passed']
digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
for name, expected in report['input_sha256'].items():
    assert digest(name) == expected, ('Producing source changed after study', name)

with np.load(record/'record.npz', allow_pickle=False) as source:
    arrays = {name: source[name] for name in source.files}
times = arrays['time']
indices = sorted(set([0, 1, 17, 317, 2048, *[int(np.searchsorted(times,t)) for t in arrays['special_times']]]))

def graph_metadata(observer, clock, kind='edges'):
    result = {'kind':kind, 'components':len(observer.components()),
              'spectralGap':observer.spectral_gap(clock.populations)}
    if kind=='edges':
        visible = observer.emphasis > 0
        result.update(edges=observer.edges[visible].tolist(), emphasis=observer.emphasis[visible].tolist())
    return result

models = {}
for name, prefix, clock in [('four','four',four_level_clock()), ('thirtyTwo','thirty_two',thirty_two_level_clock())]:
    if name=='four':
        graph_specs = {'disconnected':bridge_observer(0.), 'connected':bridge_observer(1.),
                       'weak':bridge_observer(1e-6), 'complete':complete_observer(4)}
        R_keys = {'disconnected':'four_R_bridge_0', 'connected':'four_R_bridge_1',
                  'weak':'four_R_bridge_1e-06', 'complete':'four_R_complete'}
        groups = [0,0,1,1]
    else:
        graph_specs = {'disconnected':group_observer(), 'connected':group_observer(True),
                       'complete':complete_observer(32)}
        R_keys = {key:'thirty_two_R_'+key for key in graph_specs}
        groups = [group for group in range(4) for _ in range(8)]
    metadata = {key:graph_metadata(observer,clock,'complete' if key=='complete' else 'edges')
                for key,observer in graph_specs.items()}
    states = arrays[prefix+'_states']
    references = []
    for index in indices:
        state = states[index]
        pair = state[0]*state[-1].conjugate()
        references.append({'time':float(times[index]), 'real':state.real.tolist(),
                           'imaginary':state.imag.tolist(),
                           'distanceSquared':float(arrays[prefix+'_density_distance_squared'][index]),
                           'R':{key:float(arrays[array_name][index]) for key,array_name in R_keys.items()},
                           'firstLastCoherence':{'real':float(pair.real),'imaginary':float(pair.imag)}})
    models[name] = {'id':name, 'energies':clock.energies.tolist(), 'populations':clock.populations.tolist(),
                    'groups':groups, 'graphs':metadata, 'references':references}

noise_references = []
for row in report['bounded_noise_cases']:
    if row['emphasis'] in (1e-6,1.):
        noise_references.append({'graph':'weak' if row['emphasis']==1e-6 else 'connected',
                                 'kind':row['kind'], 'measuredR':row['measured_discrepancy'],
                                 'errorNorm':row['error_norm'], 'upperBound':row['distance_bound']})
fixture = {'format':'palimpsest-relational-clock-web','version':1,
           'units':report['units'],
           'scope':'Calculated ensemble expectations of a finite pure-state model; observation selection does not alter the state.',
           'source':{'record':'relational-clock-001','reportSha256':digest(record/'report.json'),
                     'arraysSha256':digest(record/'record.npz'),
                     'protocolSha256':report['input_sha256']['research/RELATIONAL-CLOCK-PROTOCOL.md']},
           'models':models,'noiseReferences':noise_references}
target = Path(sys.argv[1])
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(fixture,separators=(',',':'),allow_nan=False)+'\n')
print(json.dumps({'fixture':str(target),'bytes':target.stat().st_size,'sha256':digest(target)}))
`;
  process.stdout.write(execFileSync(python, ['-c', producer, fileURLToPath(fixtureUrl)], {
    cwd: projectRoot,
    env: { ...process.env, OPENBLAS_NUM_THREADS: '2', OMP_NUM_THREADS: '2' },
    encoding: 'utf8',
  }));
}

const fixture = JSON.parse(readFileSync(fixtureUrl, 'utf8'));
assert.equal(fixture.format, 'palimpsest-relational-clock-web');
assert.equal(fixture.version, 1);
const core = readFileSync(coreUrl, 'utf8');
const { createRelationalClock } = await import(`data:text/javascript;base64,${Buffer.from(core).toString('base64')}`);
const errors = { state: 0, distanceSquared: 0, graphR: 0, coherence: 0, noiseBound: 0 };
let checkedStates = 0;
let checkedObservations = 0;
for (const specification of Object.values(fixture.models)) {
  const clock = createRelationalClock(specification);
  assert(Object.isFrozen(clock));
  assert(Object.isFrozen(clock.parameters.energies));
  for (const reference of specification.references) {
    const current = clock.state(reference.time);
    const before = JSON.stringify(current);
    assert(Object.isFrozen(current));
    assert(Object.isFrozen(current.real));
    assert(Object.isFrozen(current.imaginary));
    for (let index = 0; index < specification.energies.length; index += 1) {
      errors.state = Math.max(errors.state, Math.abs(current.real[index] - reference.real[index]),
        Math.abs(current.imaginary[index] - reference.imaginary[index]));
    }
    errors.distanceSquared = Math.max(errors.distanceSquared, Math.abs(clock.distanceSquared(current) - reference.distanceSquared));
    const pair = clock.coherence(current, 0, specification.energies.length - 1);
    errors.coherence = Math.max(errors.coherence, Math.abs(pair.real - reference.firstLastCoherence.real),
      Math.abs(pair.imaginary - reference.firstLastCoherence.imaginary));
    for (const [id, expectedR] of Object.entries(reference.R)) {
      const measured = clock.measure(current, id);
      errors.graphR = Math.max(errors.graphR, Math.abs(measured.discrepancy - expectedR));
      if (clock.graphs[id].components === 1) {
        assert(measured.certificate.available);
        assert(measured.certificate.upperBound >= measured.distance - 2e-11);
      } else {
        assert.equal(measured.certificate.available, false);
        assert.equal(measured.certificate.upperBound, null);
      }
      checkedObservations += 1;
    }
    assert.equal(JSON.stringify(current), before, 'Observing must not alter the state');
    assert.throws(() => { current.real[0] = 0; }, TypeError);
    assert.throws(() => clock.distance({ ...current }), TypeError);
    checkedStates += 1;
  }
  assert.throws(() => clock.state(NaN), TypeError);
  assert.throws(() => clock.state(Infinity), TypeError);
  assert.throws(() => clock.state('2'), TypeError);
  assert.throws(() => clock.certificate('connected', -1), RangeError);
  assert.throws(() => clock.certificate('connected', 0, -1), RangeError);
  assert.throws(() => clock.graphR(clock.state(0), 'absent'), RangeError);
}

const four = createRelationalClock(fixture.models.four);
const returnedFragment = four.state(2 * Math.PI);
assert(four.graphR(returnedFragment, 'disconnected') < 1e-24);
assert(four.distance(returnedFragment) > .9);
assert(four.graphR(returnedFragment, 'connected') > .2);
const sameState = JSON.stringify(returnedFragment);
for (const row of fixture.noiseReferences) {
  const result = four.certificate(row.graph, row.measuredR, row.errorNorm);
  errors.noiseBound = Math.max(errors.noiseBound, Math.abs(result.upperBound - row.upperBound));
  assert(result.upperBound >= four.distance(returnedFragment) - 2e-11);
}
assert.equal(JSON.stringify(returnedFragment), sameState);
assert.throws(() => createRelationalClock(fixture.models.thirtyTwo).distance(returnedFragment), TypeError);

const mutableSpecification = JSON.parse(JSON.stringify(fixture.models.four));
const isolated = createRelationalClock(mutableSpecification);
const isolatedBefore = JSON.stringify(isolated.state(1));
mutableSpecification.energies[1] = 999;
mutableSpecification.populations[0] = .8;
mutableSpecification.graphs.connected.emphasis[0] = 999;
assert.equal(JSON.stringify(isolated.state(1)), isolatedBefore);
assert.equal(isolated.graphs.connected.emphasis[0], 1);

const invalidConnectivity = JSON.parse(JSON.stringify(fixture.models.four));
invalidConnectivity.graphs.disconnected.spectralGap = .1;
assert.throws(() => createRelationalClock(invalidConnectivity), RangeError);
const invalidWeights = JSON.parse(JSON.stringify(fixture.models.four));
invalidWeights.graphs.connected.emphasis[0] = -1;
assert.throws(() => createRelationalClock(invalidWeights), RangeError);
const invalidSupport = JSON.parse(JSON.stringify(fixture.models.four));
invalidSupport.populations[0] = 0;
assert.throws(() => createRelationalClock(invalidSupport), RangeError);

for (const [kind, value] of Object.entries(errors)) assert(value <= 2e-12, `${kind} disagrees with the Python record by ${value}`);
console.log(JSON.stringify({ passed: true, checkedStates, checkedObservations, maximumAbsoluteErrors: errors,
  scope: 'Dependency-free browser arithmetic versus the admitted remote Python/density-matrix record; immutable states and graph metadata.' }));
