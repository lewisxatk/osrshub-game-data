#!/usr/bin/env python3
"""Build quest prerequisite/dependent graph with explicit unresolved facts."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DIST=ROOT/"dist"; REPORTS=ROOT/"reports"
def canonical(value): return " ".join(str(value).casefold().split())
def parse_requirement(value):
    if not isinstance(value,str) or not value.strip(): return None,None
    value=" ".join(value.split())
    if value.casefold().startswith("started:"):
        name=value.split(":",1)[1].strip()
        return (canonical(name),"started") if name else (None,None)
    return canonical(value),"completed"
def find_cycles(graph):
    state={}; cycles=set()
    for start in sorted(graph):
        if state.get(start,0): continue
        path=[start]; pos={start:0}; state[start]=1
        stack=[(start,iter(x["quest_key"] for x in graph[start]["prerequisites"]))]
        while stack:
            node,edges=stack[-1]
            try: child=next(edges)
            except StopIteration:
                stack.pop(); state[node]=2; pos.pop(node,None)
                if path and path[-1]==node: path.pop()
                continue
            if child not in graph: continue
            cs=state.get(child,0)
            if cs==0:
                state[child]=1; pos[child]=len(path); path.append(child)
                stack.append((child,iter(x["quest_key"] for x in graph[child]["prerequisites"])))
            elif cs==1:
                body=tuple(path[pos[child]:])
                if body:
                    rotations=[body[i:]+body[:i] for i in range(len(body))]
                    norm=min(rotations); cycles.add(norm+(norm[0],))
    return sorted(cycles)
def build_graph(quests):
    by_key={}; by_name=defaultdict(list)
    for i,q in enumerate(quests):
        if not isinstance(q,dict): raise ValueError(f"quests[{i}] must be an object")
        key,name=q.get("key"),q.get("name")
        if not isinstance(key,str) or not key.strip(): raise ValueError(f"quests[{i}] has no valid key")
        if not isinstance(name,str) or not name.strip(): raise ValueError(f"quests[{i}] has no valid name")
        if key in by_key: raise ValueError(f"duplicate quest key: {key}")
        by_key[key]=q; by_name[canonical(name)].append(key)
    deps=defaultdict(set); graph={}; unresolved=[]
    for key,q in by_key.items():
        raw=q.get("requirements",[]); prereqs={}; unres=[]
        if not isinstance(raw,list):
            item=repr(raw); unres.append(item); unresolved.append({"quest_key":key,"requirement":item,"reason":"malformed_requirement_list"}); raw=[]
        for req in raw:
            name,stage=parse_requirement(req)
            if name is None:
                unres.append(str(req)); unresolved.append({"quest_key":key,"requirement":req,"reason":"invalid_requirement"}); continue
            matches=by_name.get(name,[])
            if len(matches)==1:
                pk=matches[0]
                if pk==key:
                    unres.append(str(req)); unresolved.append({"quest_key":key,"requirement":req,"reason":"self_reference"})
                else: prereqs[pk]=stage; deps[pk].add(key)
            elif len(matches)>1:
                unres.append(str(req)); unresolved.append({"quest_key":key,"requirement":req,"reason":"ambiguous_name","candidate_keys":sorted(matches)})
            else:
                unres.append(str(req)); unresolved.append({"quest_key":key,"requirement":req,"reason":"not_found"})
        graph[key]={"quest_key":key,"name":q["name"],"prerequisites":[{"quest_key":pk,"name":by_key[pk]["name"],"completion_state":stage} for pk,stage in sorted(prereqs.items())],"dependents":[],"unresolved_requirements":sorted(set(unres),key=str.casefold),"skill_requirements":q.get("skill_requirements",[]),"source_url":q.get("source_url")}
    for key in graph: graph[key]["dependents"]=[{"quest_key":child,"name":by_key[child]["name"]} for child in sorted(deps.get(key,set()))]
    cycles=find_cycles(graph)
    duplicates=[{"name":by_key[keys[0]]["name"],"quest_keys":sorted(keys)} for keys in by_name.values() if len(keys)>1]
    rows=[graph[k] for k in sorted(graph,key=lambda k:(graph[k]["name"].casefold(),k))]
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"failed" if cycles else "passed","quest_count":len(quests),"quests_with_prerequisites":sum(bool(r["prerequisites"]) for r in rows),"resolved_prerequisite_edges":sum(len(r["prerequisites"]) for r in rows),"unresolved_requirement_count":len(unresolved),"unresolved_requirements":unresolved[:200],"unresolved_examples_truncated":len(unresolved)>200,"duplicate_name_groups":duplicates,"cycle_count":len(cycles),"cycles":[list(c) for c in cycles[:50]],"note":"Name-matched relationships are not proof of factual completeness; unresolved facts remain warnings."}
    return rows,report
def main():
    try:
        quests=json.loads((DIST/"quests.json").read_text(encoding="utf-8"))
        if not isinstance(quests,list): raise ValueError("dist/quests.json must be a JSON array")
        rows,report=build_graph(quests)
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        rows=[]; report={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"failed","quest_count":0,"quests_with_prerequisites":0,"resolved_prerequisite_edges":0,"unresolved_requirement_count":0,"unresolved_requirements":[],"unresolved_examples_truncated":False,"duplicate_name_groups":[],"cycle_count":0,"cycles":[],"errors":[str(exc)],"note":"Quest relationship graph could not be built."}
    DIST.mkdir(parents=True,exist_ok=True); REPORTS.mkdir(parents=True,exist_ok=True)
    (DIST/"quest-relationships.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REPORTS/"quest-relationship-coverage.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2)); return 1 if report["status"]=="failed" else 0
if __name__=="__main__": raise SystemExit(main())
