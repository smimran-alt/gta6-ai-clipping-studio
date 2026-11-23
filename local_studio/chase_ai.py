"""Optional local CLIP vision-based ranking for car-chase footage.

Image/text similarity is a heuristic, NOT a trained event classifier. The model
may misidentify footage. Audio and movement are evaluated separately by highlights.
"""
from pathlib import Path
import io
import subprocess

PROMPTS={
    "car_chase":[
        "Video game screenshot of a fast car chase with several cars pursuing each other",
        "Video game screenshot of police cars chasing a fleeing car on a city road",
        "Video game screenshot of a vehicle pursuit at high speed on a highway",
    ],
    "sensational":[
        "Video game screenshot of a spectacular vehicle crash with cars colliding",
        "Video game screenshot of a dramatic car stunt, jump or near collision",
        "Video game screenshot of an explosion during an action-packed driving scene",
    ],
    "ordinary":[
        "Video game screenshot of a parked car on a quiet empty street",
        "Video game screenshot of calm routine driving with no pursuit",
        "Video game screenshot of a character standing still or a video game menu",
    ],
}

def _frame(source,second):
    from PIL import Image
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
         "-ss",str(max(0,second)),"-i",str(source),"-frames:v","1",
         "-vf","scale=320:-2","-f","image2pipe","-vcodec","mjpeg","-"]
    result=subprocess.run(cmd,capture_output=True,timeout=35)
    if result.returncode or not result.stdout:
        raise RuntimeError(result.stderr.decode("utf-8","replace")[-400:])
    return Image.open(io.BytesIO(result.stdout)).convert("RGB")

def analyze_candidates(source,candidates,model_name="openai/clip-vit-base-patch32",progress=None):
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor
    except ImportError as exc:
        raise RuntimeError("Install optional AI dependencies: pip install -r local_studio/requirements_ai.txt") from exc
    model=CLIPModel.from_pretrained(model_name).eval()
    processor=CLIPProcessor.from_pretrained(model_name)
    prompts=[p for group in PROMPTS.values() for p in group]
    text_inputs=processor(text=prompts,return_tensors="pt",padding=True,truncation=True)
    with torch.no_grad():
        text_features=model.get_text_features(**text_inputs)
        if not isinstance(text_features,torch.Tensor):
            text_features=text_features.pooler_output
        text_features=torch.nn.functional.normalize(text_features,dim=-1)
    results=[]
    for i,item in enumerate(candidates):
        frames=[]
        for offset in (1,5,11,18,25):
            try:frames.append(_frame(source,float(item["start"])+offset))
            except (RuntimeError,subprocess.TimeoutExpired):pass
        if not frames:
            results.append({**item,"chase_score":None,"sensational_score":None,
                            "ai_reason":"No readable video frames","ai_score":None})
            continue
        with torch.no_grad():
            img_inputs=processor(images=frames,return_tensors="pt")
            img_features=model.get_image_features(**img_inputs)
            if not isinstance(img_features,torch.Tensor):
                img_features=img_features.pooler_output
            img_features=torch.nn.functional.normalize(img_features,dim=-1)
            sims=(img_features @ text_features.T).cpu()
        # CLIP similarity is relative to the supplied prompts; softmax is NOT probability.
        probabilities=torch.softmax(sims*15,dim=1)
        chase=float(probabilities[:,:3].sum(dim=1).mean())
        spectacular=float(probabilities[:,3:6].sum(dim=1).mean())
        ordinary=float(probabilities[:,6:9].sum(dim=1).mean())
        # 30% pursuit + 20% crashes/stunts + 15% visual action; remaining
        # 35% uses the existing hook/pacing/audio proxies. These are estimates.
        visual_action=max(chase,spectacular)
        proxy=float(item.get("score",0))/100
        combined=round(100*(.30*chase+.20*spectacular+.15*visual_action+.35*proxy),1)
        reason=("Possible pursuit / chase visuals" if chase>=spectacular else
                "Possible dramatic crash / stunt visuals")
        results.append({**item,"chase_score":round(chase*100,1),
                        "sensational_score":round(spectacular*100,1),
                        "ordinary_score":round(ordinary*100,1),
                        "ai_score":combined,
                        "ai_reason":reason+" (CLIP image-text similarity; verify manually)"})
        if progress:progress(i+1,len(candidates))
    results.sort(key=lambda x: (-(x["ai_score"] if x["ai_score"] is not None else -1),x["start"]))
    selected=[]
    for item in results:
        if all(abs(item["start"]-other["start"])>=30 for other in selected):
            selected.append(item)
    return selected
