"""Small paired-outcome record derived from the full saved experiment."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from studio.preserve import sha256


def main(args):
    study, output = Path(args.study), Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    report = json.loads((study / 'report.json').read_text())
    cases = []
    for rate in (96, 192):
        for severity in (.01, .03, .10):
            path = study / f'rate-{rate}' / f'pressure-{round(severity * 100):02d}' / 'identification.npz'
            with np.load(path) as data:
                nearest = data['baseline_predicted'] == data['truth']
                corrected = data['corrected_predicted'] == data['truth']
                adjustments = np.abs(data['winning_pressure_adjustments']).max(axis=1)
                cases.append({'rate': rate, 'pressure_limit': severity, 'tested': len(nearest),
                              'both_correct': int(np.count_nonzero(nearest & corrected)),
                              'recovered_by_correction': int(np.count_nonzero(~nearest & corrected)),
                              'lost_by_correction': int(np.count_nonzero(nearest & ~corrected)),
                              'both_wrong': int(np.count_nonzero(~nearest & ~corrected)),
                              'winning_adjustment_outside_actual_severity': int(np.count_nonzero(adjustments > severity)),
                              'maximum_absolute_winning_adjustment': float(adjustments.max()),
                              'source_sha256': sha256(path)})
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'study_report_sha256': sha256(study / 'report.json'),
              'seed': report['seed'], 'cases': cases,
              'interpretation': 'Paired counts for exactly the same finite cases. The local linear adjustment is unconstrained and is not a recovered physical pressure. No statistical-population or perceptual claim.'}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', default='artifacts/studies/pressure-reading-001')
    parser.add_argument('--output', default='research/pressure-paired-001.json')
    main(parser.parse_args())
