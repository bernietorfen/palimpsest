"""Copy a verified public asset inventory into the exhibition directory."""
import argparse
import json
from pathlib import Path
import shutil

from studio.preserve import sha256


def main(args):
    source=Path(args.source).resolve()
    inventory=json.loads((source/"manifest.json").read_text())["files"]
    for item in inventory:
        name=item["name"]
        path=source/name
        if Path(name).name!=name or path.is_symlink() or name.startswith("."):
            raise ValueError("asset inventory contains an unsafe path")
        if path.stat().st_size!=item["bytes"] or sha256(path)!=item["sha256"]:
            raise ValueError(f"asset changed after inventory: {name}")
    destination=Path(args.site)/"assets"/"generated"
    destination.mkdir(parents=True,exist_ok=True)
    for item in inventory:
        target=destination/item["name"]
        temporary=target.with_name(target.name+".staging")
        shutil.copy2(source/item["name"],temporary)
        temporary.replace(target)
    print(json.dumps({"staged":len(inventory),"bytes":sum(item["bytes"] for item in inventory),
                      "destination":str(destination)}),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--site",default="site")
    main(parser.parse_args())
