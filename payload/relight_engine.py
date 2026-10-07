from pathlib import Path
import argparse, sys, math
import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageCms

ROOT=Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
cv2.setNumThreads(2)

# ---------------- IO / COLOR ----------------

def read_image(path):
    data=np.fromfile(str(path),dtype=np.uint8)
    im=cv2.imdecode(data,cv2.IMREAD_COLOR)
    if im is None:
        raise ValueError("Cannot decode input")
    return im

def srgb_profile_bytes():
    try:
        return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    except Exception:
        return None

def write_image(path,im):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    rgb=cv2.cvtColor(im,cv2.COLOR_BGR2RGB)
    image=Image.fromarray(rgb)
    icc=srgb_profile_bytes()
    if p.suffix.lower() in (".tif",".tiff"):
        kw={"compression":"tiff_lzw"}
        if icc:
            kw["icc_profile"]=icc
        image.save(str(p),format="TIFF",**kw)
    else:
        kw={"quality":96,"subsampling":0}
        if icc:
            kw["icc_profile"]=icc
        image.save(str(p),format="JPEG",**kw)

def ort_session(path):
    so=ort.SessionOptions()
    so.intra_op_num_threads=2
    so.inter_op_num_threads=1
    so.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(path),sess_options=so,providers=["CPUExecutionProvider"])

# ---------------- AI MODELS ----------------

class MODNet:
    def __init__(self):
        self.session=ort_session(ROOT/"models"/"modnet_photographic.onnx")
        self.input=self.session.get_inputs()[0].name
        self.outputs=[x.name for x in self.session.get_outputs()]

    def predict(self,bgr):
        h,w=bgr.shape[:2]
        rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
        target=512
        if w>=h:
            nh=target
            nw=max(32,int(w/h*target))
        else:
            nw=target
            nh=max(32,int(h/w*target))
        nh-=nh%32
        nw-=nw%32
        x=cv2.resize(rgb,(nw,nh),interpolation=cv2.INTER_AREA).astype(np.float32)/255.0
        x=(x-.5)/.5
        x=np.transpose(x,(2,0,1))[None]
        matte=self.session.run(self.outputs,{self.input:x})[0]
        matte=np.squeeze(matte).astype(np.float32,copy=False)
        matte=cv2.resize(matte,(w,h),interpolation=cv2.INTER_CUBIC).astype(np.float32,copy=False)
        matte=np.ascontiguousarray(np.clip(matte,0,1),dtype=np.float32)
        matte=cv2.GaussianBlur(matte,(0,0),1.1).astype(np.float32,copy=False)
        return np.clip(matte,0,1).astype(np.float32,copy=False)

class DepthAnythingV2:
    def __init__(self):
        self.session=ort_session(ROOT/"models"/"depth_anything_v2_vits.onnx")
        self.input=self.session.get_inputs()[0].name
        self.output=self.session.get_outputs()[0].name

    def predict(self,bgr):
        h,w=bgr.shape[:2]
        rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
        x=cv2.resize(rgb,(518,518),interpolation=cv2.INTER_CUBIC).astype(np.float32)/255.0
        mean=np.array([0.485,0.456,0.406],dtype=np.float32)
        std=np.array([0.229,0.224,0.225],dtype=np.float32)
        x=(x-mean)/std
        x=np.transpose(x,(2,0,1))[None]
        d=np.squeeze(self.session.run([self.output],{self.input:x})[0]).astype(np.float32,copy=False)
        d=cv2.resize(d,(w,h),interpolation=cv2.INTER_CUBIC).astype(np.float32,copy=False)
        p=np.percentile(d,[2,98]).astype(np.float32)
        d=(d-p[0])/(p[1]-p[0]+np.float32(1e-6))
        d=np.clip(d,0,1).astype(np.float32,copy=False)
        d=np.ascontiguousarray(d,dtype=np.float32)
        return cv2.GaussianBlur(d,(0,0),2.0).astype(np.float32,copy=False)

class FaceDetector:
    def __init__(self):
        self.detector=None
        model=ROOT/"models"/"face_detection_yunet_2023mar.onnx"
        try:
            self.detector=cv2.FaceDetectorYN_create(str(model),"",(320,320),0.72,0.3,5000)
        except Exception:
            self.detector=None

    def mask(self,bgr):
        h,w=bgr.shape[:2]
        mask=np.zeros((h,w),dtype=np.float32)
        if self.detector is None:
            return mask
        scale=min(1.0,1000.0/max(h,w))
        small=cv2.resize(bgr,(max(1,int(w*scale)),max(1,int(h*scale)))) if scale<1 else bgr
        sh,sw=small.shape[:2]
        try:
            self.detector.setInputSize((sw,sh))
            _,faces=self.detector.detect(small)
        except Exception:
            return mask
        if faces is None:
            return mask
        for f in faces:
            x,y,bw,bh=f[:4]/scale
            cx=x+bw*.5
            cy=y+bh*.50
            rx=max(3,bw*.63)
            ry=max(3,bh*.78)
            yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
            ellipse=1.0-(((xx-cx)/rx)**2+((yy-cy)/ry)**2)
            mask=np.maximum(mask,np.clip(ellipse,0,1).astype(np.float32))
        return cv2.GaussianBlur(mask,(0,0),max(1.2,min(h,w)*.004)).astype(np.float32,copy=False)

# ---------------- GEOMETRY / MASKS ----------------

def subject_center(alpha):
    ys,xs=np.where(alpha>.20)
    h,w=alpha.shape
    if len(xs)==0:
        return .5,.5
    weights=alpha[ys,xs]
    return float(np.average(xs,weights=weights)/max(w-1,1)),float(np.average(ys,weights=weights)/max(h-1,1))

def normals_from_depth(depth):
    depth=np.ascontiguousarray(depth,dtype=np.float32)
    dzdx=cv2.Sobel(depth,cv2.CV_32F,1,0,ksize=3)
    dzdy=cv2.Sobel(depth,cv2.CV_32F,0,1,ksize=3)
    nx=-dzdx*2.0
    ny=-dzdy*2.0
    nz=np.ones_like(depth,dtype=np.float32)
    n=np.stack([nx,ny,nz],axis=-1).astype(np.float32)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)+np.float32(1e-6)
    return n

def world_grid(depth):
    h,w=depth.shape
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    x=(xx/max(w-1,1)-.5)*2.0
    y=(yy/max(h-1,1)-.5)*2.0
    z=.12+.95*depth
    return np.stack([x,y,z],axis=-1).astype(np.float32)

def depth_zones(depth):
    # Relative depth bands; each is soft and normalized.
    near=np.clip((depth-.58)/.25,0,1).astype(np.float32)
    far=np.clip((.45-depth)/.25,0,1).astype(np.float32)
    mid=np.clip(1.0-near-far,0,1).astype(np.float32)
    return near,mid,far

def edge_rim(alpha,light_x,diffusion):
    a=np.ascontiguousarray(alpha,dtype=np.float32)
    gx=cv2.Sobel(a,cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(a,cv2.CV_32F,0,1,ksize=3)
    mag=np.sqrt(gx*gx+gy*gy).astype(np.float32)
    sign=np.float32(1.0 if light_x>.5 else -1.0)
    facing=np.clip(sign*gx/(mag+np.float32(1e-6)),0,1).astype(np.float32)
    rim=np.clip(mag*5.3,0,1)*facing
    rim=np.ascontiguousarray(rim,dtype=np.float32)
    return cv2.GaussianBlur(rim,(0,0),float(1.5+5.0*diffusion)).astype(np.float32,copy=False)

def expanded_subject(alpha,amount):
    radius=max(3,int(min(alpha.shape)*amount))
    k=radius*2+1
    if k>101: k=101
    return cv2.GaussianBlur(alpha,(0,0),max(2.0,radius*.35)).astype(np.float32,copy=False)

# ---------------- COLOR / LIGHT ----------------

def kelvin_bgr(k):
    k=float(np.clip(k,1000,12000))/100.0
    if k<=66:
        r=255.0
        g=99.4708025861*np.log(max(k,1e-6))-161.1195681661
        b=0.0 if k<=19 else 138.5177312231*np.log(max(k-10,1e-6))-305.0447927307
    else:
        r=329.698727446*((k-60)**-0.1332047592)
        g=288.1221695283*((k-60)**-0.0755148492)
        b=255.0
    return np.clip(np.array([b,g,r],dtype=np.float32)/255.0,0,1)

def light_field(depth,normals,lx,ly,lz,diffusion):
    pos=world_grid(depth)
    light=np.array([(lx-.5)*2.5,(ly-.5)*2.5,lz],dtype=np.float32)
    vec=light.reshape(1,1,3)-pos
    dist=np.linalg.norm(vec,axis=-1)+np.float32(1e-5)
    direction=vec/dist[...,None]
    lambert=np.clip(np.sum(normals*direction,axis=-1),0,1).astype(np.float32)
    wrap=np.float32(.05+.62*np.clip(diffusion,0,1))
    directional=np.clip((lambert+wrap)/(1.0+wrap),0,1).astype(np.float32)
    attenuation=(1.0/(1.0+0.42*dist*dist)).astype(np.float32)
    return directional*attenuation

def radial_2d(h,w,x,y,sigma):
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    xx/=max(w-1,1)
    yy/=max(h-1,1)
    d2=(xx-x)**2+(yy-y)**2
    return np.exp(-d2/(2*sigma*sigma)).astype(np.float32)

def apply_exposure(img,stops,mask):
    factor=np.float32(2.0**float(stops))
    m=np.clip(mask,0,1)[...,None].astype(np.float32)
    return np.clip(img*(1-m)+img*factor*m,0,1)

def apply_temperature(img,amount,mask):
    a=np.float32(np.clip(amount,-1,1))
    if abs(float(a))<1e-6:
        return img
    # BGR multipliers: positive = warm, negative = cool.
    warm=np.array([.82,1.0,1.18],dtype=np.float32)
    cool=np.array([1.18,1.0,.84],dtype=np.float32)
    tint=warm if a>=0 else cool
    strength=abs(float(a))
    mult=1.0+(tint-1.0)*strength
    m=np.clip(mask,0,1)[...,None].astype(np.float32)
    return np.clip(img*(1-m)+img*mult.reshape(1,1,3)*m,0,1)

def apply_light(img,field,color,gain):
    f=np.clip(field,0,1)[...,None].astype(np.float32)
    color=color.reshape(1,1,3).astype(np.float32)
    # Shape luminance strongly enough to read as relighting, while retaining texture.
    luminance=1.0+f*np.float32(gain)
    chroma=1.0+(color-.70)*f*np.float32(gain*.42)
    return np.clip(img*luminance*chroma,0,1)

def shadow_shape(img,amount,mask=None):
    a=np.clip(amount,0,1)
    if a<=0:
        return img
    lum=cv2.cvtColor((np.clip(img,0,1)*255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    shadows=np.clip((.62-lum)/.62,0,1).astype(np.float32)
    if mask is not None:
        shadows*=np.clip(mask,0,1).astype(np.float32)
    m=(shadows*a*.48)[...,None]
    return np.clip(img*(1-m),0,1)

def creative_contrast(img,amount):
    a=np.clip(amount,0,1)
    if a<=0:
        return img
    # smooth S curve around middle gray
    x=np.clip(img,0,1)
    s=x*x*(3.0-2.0*x)
    return np.clip(x*(1-a*.52)+s*(a*.52),0,1)

def saturation(img,amount):
    a=np.clip(amount,-1,1)
    if abs(float(a))<1e-6:
        return img
    hsv=cv2.cvtColor((np.clip(img,0,1)*255).astype(np.uint8),cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[...,1]=np.clip(hsv[...,1]*(1.0+a*.55),0,255)
    return cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2BGR).astype(np.float32)/255.0

def highlight_soften(img,amount):
    a=np.clip(amount,0,1)
    if a<=0:
        return img
    x=np.clip(img,0,1)
    threshold=.72
    over=np.clip((x-threshold)/(1-threshold),0,1)
    compressed=threshold+(1-threshold)*(1-np.exp(-over*1.55))/ (1-np.exp(-1.55))
    mask=np.clip((x-threshold)/(1-threshold),0,1)*a
    return np.clip(x*(1-mask)+compressed*mask,0,1)

def bloom(img,amount):
    a=np.clip(amount,0,1)
    if a<=0:
        return img
    lum=cv2.cvtColor((np.clip(img,0,1)*255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    bright=np.clip((lum-.68)/.32,0,1)
    bright=(bright*bright).astype(np.float32)
    sigma=max(3.0,min(img.shape[:2])*.018)
    glow=cv2.GaussianBlur((img*bright[...,None]).astype(np.float32),(0,0),sigma)
    return np.clip(img+glow*(a*.32),0,1)

def vignette(img,amount):
    a=np.clip(amount,0,1)
    if a<=0:
        return img
    h,w=img.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    dx=(xx/(w-1 if w>1 else 1)-.5)/.5
    dy=(yy/(h-1 if h>1 else 1)-.5)/.5
    r=np.sqrt(dx*dx+dy*dy)
    v=np.clip((r-.35)/.75,0,1)**1.7
    mult=1.0-v*a*.42
    return np.clip(img*mult[...,None],0,1)

# ---------------- PRESETS ----------------

PRESETS={
    "luxury_warm":{
        "key_x":-.25,"key_y":-.16,"key_k":4100,"key_i":.86,"key_d":.62,
        "fill_i":.27,"fill_k":5700,"rim_i":.32,"rim_k":3400,
        "bg_ev":-.38,"bg_temp":.28,"shadow":.30,"spill":.31,"sep":.38,
        "contrast":.27,"bloom":.13,"vignette":.18,"sat":.22
    },
    "golden_hour":{
        "key_x":-.34,"key_y":-.12,"key_k":3600,"key_i":.88,"key_d":.55,
        "fill_i":.20,"fill_k":5200,"rim_i":.72,"rim_k":3000,
        "bg_ev":-.12,"bg_temp":.48,"shadow":.20,"spill":.58,"sep":.24,
        "contrast":.24,"bloom":.25,"vignette":.10,"sat":.30
    },
    "moody_indoor":{
        "key_x":-.28,"key_y":-.18,"key_k":4000,"key_i":.72,"key_d":.48,
        "fill_i":.16,"fill_k":6500,"rim_i":.26,"rim_k":3500,
        "bg_ev":-.62,"bg_temp":.18,"shadow":.55,"spill":.18,"sep":.55,
        "contrast":.46,"bloom":.08,"vignette":.34,"sat":.12
    },
    "editorial_flash":{
        "key_x":-.02,"key_y":-.22,"key_k":5400,"key_i":1.02,"key_d":.32,
        "fill_i":.20,"fill_k":6500,"rim_i":.12,"rim_k":6500,
        "bg_ev":-.28,"bg_temp":-.18,"shadow":.28,"spill":.10,"sep":.45,
        "contrast":.52,"bloom":.06,"vignette":.12,"sat":.05
    },
    "bridal_glow":{
        "key_x":-.18,"key_y":-.18,"key_k":4400,"key_i":.72,"key_d":.78,
        "fill_i":.36,"fill_k":5600,"rim_i":.24,"rim_k":3900,
        "bg_ev":-.16,"bg_temp":.16,"shadow":.13,"spill":.24,"sep":.22,
        "contrast":.16,"bloom":.30,"vignette":.08,"sat":.12
    },
    "dark_cinematic":{
        "key_x":-.38,"key_y":-.10,"key_k":3900,"key_i":.96,"key_d":.30,
        "fill_i":.10,"fill_k":7800,"rim_i":.58,"rim_k":7600,
        "bg_ev":-.78,"bg_temp":-.23,"shadow":.68,"spill":.12,"sep":.68,
        "contrast":.66,"bloom":.06,"vignette":.42,"sat":-.05
    },
    "cool_premium":{
        "key_x":-.22,"key_y":-.16,"key_k":6000,"key_i":.78,"key_d":.60,
        "fill_i":.26,"fill_k":7600,"rim_i":.34,"rim_k":7000,
        "bg_ev":-.34,"bg_temp":-.34,"shadow":.26,"spill":.22,"sep":.42,
        "contrast":.32,"bloom":.09,"vignette":.20,"sat":-.08
    },
    "sunset_drama":{
        "key_x":-.42,"key_y":-.05,"key_k":3300,"key_i":.93,"key_d":.44,
        "fill_i":.14,"fill_k":6200,"rim_i":.88,"rim_k":2800,
        "bg_ev":-.26,"bg_temp":.60,"shadow":.38,"spill":.68,"sep":.32,
        "contrast":.43,"bloom":.24,"vignette":.22,"sat":.36
    }
}

def choose_auto(im,alpha,depth):
    gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    bg=1.0-alpha
    sb=float(np.sum(alpha))+1e-6
    bb=float(np.sum(bg))+1e-6
    subject_mean=float(np.sum(gray*alpha)/sb)
    bg_mean=float(np.sum(gray*bg)/bb)
    warm=np.mean(im[...,2].astype(np.float32)-im[...,0].astype(np.float32))
    cx,_=subject_center(alpha)

    if subject_mean<.27:
        return "moody_indoor"
    if bg_mean>.68 and subject_mean>.50:
        return "editorial_flash"
    if warm>18:
        return "luxury_warm"
    if cx<.32 or cx>.68:
        return "golden_hour"
    if bg_mean<.25:
        return "dark_cinematic"
    return "bridal_glow"

# ---------------- RENDER ----------------

def build_subject_lighting(orig,alpha,depth,normals,face_mask,mode,preset_name,cfg):
    h,w=alpha.shape
    cx,cy=subject_center(alpha)
    subject_strength=np.clip(cfg["subjectStrength"]/100.0,0,1)
    rim_strength=np.clip(cfg["rimStrength"]/100.0,0,1)

    out=orig.copy()
    light_source=(cfg["lightX"]/100.0,cfg["lightY"]/100.0)

    if mode=="manual":
        lx=np.clip(cfg["lightX"]/100.0,0,1)
        ly=np.clip(cfg["lightY"]/100.0,0,1)
        inten=np.clip(cfg["lightIntensity"]/100.0,0,1)
        diff=np.clip(cfg["lightDiffusion"]/100.0,0,1)
        color=kelvin_bgr(cfg["lightKelvin"])
        field=light_field(depth,normals,lx,ly,1.05,diff)

        if cfg["lightType"]=="rim":
            field=edge_rim(alpha,lx,diff)
            gain=.96*inten*subject_strength*(.65+.7*rim_strength)
            field*=np.clip(alpha*1.6,0,1)
        elif cfg["lightType"]=="fill":
            field*=.82*alpha+.03
            gain=.48*inten*subject_strength
        elif cfg["lightType"]=="background":
            field*=1-alpha
            gain=.55*inten*subject_strength
        else:
            field*=.96*alpha+.025
            gain=.74*inten*subject_strength

        out=apply_light(out,field,color,gain)
        return out,light_source

    p=PRESETS[preset_name]
    lx=np.clip(cx+p["key_x"],.04,.96)
    ly=np.clip(cy+p["key_y"],.04,.90)
    light_source=(lx,ly)

    key=light_field(depth,normals,lx,ly,1.05,p["key_d"])*(.96*alpha+.025)
    out=apply_light(out,key,kelvin_bgr(p["key_k"]),p["key_i"]*subject_strength)

    fill_x=np.clip(cx-p["key_x"]*.85,.04,.96)
    fill=light_field(depth,normals,fill_x,cy,1.42,.92)*(.78*alpha+.015)
    out=apply_light(out,fill,kelvin_bgr(p["fill_k"]),p["fill_i"]*subject_strength)

    rim_x=.03 if lx>.5 else .97
    rim=edge_rim(alpha,rim_x,.34)
    rim_gain=p["rim_i"]*subject_strength*(.45+.80*rim_strength)
    out=apply_light(out,rim,kelvin_bgr(p["rim_k"]),rim_gain)

    # Face priority: brighter, softer and less saturated than the rest of subject.
    if cfg["facePriority"]>=.5 and np.max(face_mask)>.05:
        face_field=cv2.GaussianBlur(face_mask.astype(np.float32),(0,0),6.0)
        neutral=np.array([.95,1.0,1.04],dtype=np.float32)
        protected=apply_light(out,face_field,neutral,.14*subject_strength)
        out=out*(1-face_field[...,None]*.45)+protected*(face_field[...,None]*.45)

    return np.clip(out,0,1),light_source

def scene_relight(img,orig,alpha,depth,light_source,preset_name,cfg,mode):
    near,mid,far=depth_zones(depth)
    bg=np.clip(1-alpha,0,1).astype(np.float32)
    scene=np.clip(cfg["sceneMood"]/100.0,0,1)

    # User controls are combined with preset intent in preset/auto modes.
    if mode=="manual":
        p_bg_ev=0.0
        p_bg_temp=0.0
        p_shadow=.20
        p_spill=.25
        p_sep=.30
    else:
        p=PRESETS[preset_name]
        p_bg_ev=p["bg_ev"]
        p_bg_temp=p["bg_temp"]
        p_shadow=p["shadow"]
        p_spill=p["spill"]
        p_sep=p["sep"]

    user_ev=(cfg["backgroundExposure"]/100.0)*1.55
    ev=(p_bg_ev+user_ev)*scene
    # far background responds more strongly; near background retains realism.
    img=apply_exposure(img,ev*.60,bg*near)
    img=apply_exposure(img,ev*.85,bg*mid)
    img=apply_exposure(img,ev*1.10,bg*far)

    user_temp=cfg["backgroundTemp"]/100.0
    temp=np.clip((p_bg_temp+user_temp)*scene,-1,1)
    img=apply_temperature(img,temp,bg*(.35*near+.70*mid+1.0*far))

    # Subject separation: dark/cool halo in nearby background, never on subject.
    separation=np.clip((p_sep+cfg["separation"]/100.0*.55)*scene,0,1)
    surround=expanded_subject(alpha,.035)
    halo=np.clip(surround-alpha,0,1)*bg
    img=apply_exposure(img,-.72*separation,halo)
    img=apply_temperature(img,-.24*separation,halo)

    # Light spill extends virtual light into environment with depth falloff.
    spill=np.clip((p_spill+cfg["lightSpill"]/100.0*.65)*scene,0,1)
    lx,ly=light_source
    spill_field=radial_2d(alpha.shape[0],alpha.shape[1],lx,ly,.34+.28*(1-spill))
    depth_weight=.75*near+.42*mid+.20*far
    spill_mask=spill_field*bg*depth_weight
    spill_color=kelvin_bgr(cfg["lightKelvin"] if mode=="manual" else PRESETS[preset_name]["key_k"])
    img=apply_light(img,spill_mask,spill_color,.55*spill)

    # Shadow shaping affects background more than face/subject.
    shadow=np.clip((p_shadow+cfg["shadowDepth"]/100.0*.60)*scene,0,1)
    img=shadow_shape(img,shadow,bg*(.65+.35*far))
    img=shadow_shape(img,shadow*.26,alpha)

    return np.clip(img,0,1)

def finish(img,orig,face_mask,preset_name,cfg,mode):
    if mode=="manual":
        p_contrast=.18
        p_bloom=.08
        p_vignette=.10
        p_sat=.0
    else:
        p=PRESETS[preset_name]
        p_contrast=p["contrast"]
        p_bloom=p["bloom"]
        p_vignette=p["vignette"]
        p_sat=p["sat"]

    contrast=np.clip(p_contrast+cfg["creativeContrast"]/100.0*.55,0,1)
    img=creative_contrast(img,contrast)

    color=np.clip(p_sat+cfg["colorStrength"]/100.0*.45,-.65,.75)
    img=saturation(img,color)

    soft=np.clip(cfg["highlightSoftness"]/100.0,0,1)
    img=highlight_soften(img,soft)

    bloom_amount=np.clip(p_bloom+cfg["bloom"]/100.0*.55,0,1)
    img=bloom(img,bloom_amount)

    vignette_amount=np.clip(p_vignette+cfg["vignette"]/100.0*.50,0,1)
    img=vignette(img,vignette_amount)

    # Face texture / skin protection: softly blend some original back in.
    if cfg["facePriority"]>=.5 and np.max(face_mask)>.05:
        fm=np.clip(face_mask*.52,0,.52)[...,None]
        img=img*(1-fm)+orig*fm

    # Global highlight protection.
    lum=cv2.cvtColor((np.clip(img,0,1)*255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    hp=np.clip((lum-.90)/.10,0,1)[...,None]
    img=img*(1-.48*hp)+orig*(.48*hp)

    return np.clip(img,0,1)

def render_v4(im,matte_model,depth_model,face_detector,cfg):
    orig=im.astype(np.float32)/255.0
    alpha=matte_model.predict(im)
    depth=depth_model.predict(im)
    normals=normals_from_depth(depth)
    face=face_detector.mask(im)

    mode=cfg["mode"]
    if mode=="auto":
        preset=choose_auto(im,alpha,depth)
    else:
        preset=cfg["preset"]

    out,light_source=build_subject_lighting(orig,alpha,depth,normals,face,mode,preset,cfg)
    out=scene_relight(out,orig,alpha,depth,light_source,preset,cfg,mode)
    out=finish(out,orig,face,preset,cfg,mode)

    keep=np.clip(cfg["original"]/100.0,0,1)
    out=orig*keep+out*(1-keep)

    return np.clip(out*255,0,255).astype(np.uint8),preset

# ---------------- MANIFEST ----------------

def parse_row(parts):
    if len(parts)!=27:
        raise ValueError(f"Expected 27 manifest columns, got {len(parts)}")
    sid,inp,tif,jpg,mode,preset,lightType,lightX,lightY,lightIntensity,lightDiffusion,lightKelvin,rimStrength,facePriority,subjectStrength,sceneMood,backgroundExposure,backgroundTemp,shadowDepth,lightSpill,separation,creativeContrast,bloomAmount,highlightSoftness,vignetteAmount,colorStrength,original=parts
    return sid,inp,tif,jpg,{
        "mode":mode,"preset":preset,"lightType":lightType,
        "lightX":float(lightX),"lightY":float(lightY),
        "lightIntensity":float(lightIntensity),"lightDiffusion":float(lightDiffusion),
        "lightKelvin":float(lightKelvin),"rimStrength":float(rimStrength),
        "facePriority":float(facePriority),
        "subjectStrength":float(subjectStrength),"sceneMood":float(sceneMood),
        "backgroundExposure":float(backgroundExposure),"backgroundTemp":float(backgroundTemp),
        "shadowDepth":float(shadowDepth),"lightSpill":float(lightSpill),
        "separation":float(separation),"creativeContrast":float(creativeContrast),
        "bloom":float(bloomAmount),"highlightSoftness":float(highlightSoftness),
        "vignette":float(vignetteAmount),"colorStrength":float(colorStrength),
        "original":float(original)
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--results",required=True)
    a=ap.parse_args()

    lines=Path(a.manifest).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0]!="ANAI_RELIGHT_V4_BATCH_1":
        raise ValueError("Unsupported V4 manifest")

    matte=MODNet()
    depth=DepthAnythingV2()
    face=FaceDetector()

    results=["ANAI_RELIGHT_V4_RESULTS_1"]
    hard_fail=False

    for line in lines[1:]:
        if not line.strip():
            continue
        sid="?"
        try:
            sid,inp,tif,jpg,cfg=parse_row(line.split("\t"))
            im=read_image(inp)
            out,used_preset=render_v4(im,matte,depth,face,cfg)
            write_image(tif,out)
            if jpg:
                write_image(jpg,out)
            results.append(f"{sid}\tok\tV4 {cfg['mode']} / {used_preset}: subject + scene + creative finish")
        except Exception as e:
            hard_fail=True
            msg=str(e).replace("\t"," ").replace("\r"," ").replace("\n"," ")[:600]
            results.append(f"{sid}\terror\t{msg}")

    Path(a.results).write_text("\n".join(results)+"\n",encoding="utf-8")
    raise SystemExit(2 if hard_fail else 0)

if __name__=="__main__":
    main()
