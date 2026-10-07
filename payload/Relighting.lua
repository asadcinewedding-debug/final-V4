local Binding=import 'LrBinding'
local Dialogs=import 'LrDialogs'
local Export=import 'LrExportSession'
local Files=import 'LrFileUtils'
local Path=import 'LrPathUtils'
local Progress=import 'LrProgressScope'
local Tasks=import 'LrTasks'
local UUID=import 'LrUUID'
local View=import 'LrView'
local Engine=require 'Engine'

local M={}

local PRESETS={
    auto=true,luxury_warm=true,golden_hour=true,moody_indoor=true,
    editorial_flash=true,bridal_glow=true,dark_cinematic=true,
    cool_premium=true,sunset_drama=true
}

local LIGHTS={key=true,fill=true,rim=true,background=true}

local function number(v,lo,hi,label)
    local n=tonumber(v)
    if not n or n~=n or n<lo or n>hi then
        error(label..' must be between '..lo..' and '..hi)
    end
    return n
end

function M.configure(ctx,count)
    local p=Binding.makePropertyTable(ctx)
    local f=View.osFactory()

    p.mode='auto'
    p.preset='luxury_warm'

    p.lightType='key'
    p.lightX=22
    p.lightY=28
    p.lightIntensity=78
    p.lightDiffusion=48
    p.lightKelvin=4300
    p.rimStrength=55
    p.facePriority=true

    p.subjectStrength=70
    p.sceneMood=65
    p.backgroundExposure=-20
    p.backgroundTemp=18
    p.shadowDepth=35
    p.lightSpill=32
    p.separation=38

    p.creativeContrast=25
    p.bloom=16
    p.highlightSoftness=35
    p.vignette=18
    p.colorStrength=35
    p.original=25

    p.stack=true
    p.jpeg=false
    p.quality='high'

    local content=f:column{
        bind_to_object=p,
        spacing=f:control_spacing(),

        f:static_text{title='AN AI RELIGHT V4 — CREATIVE RELIGHT',font='<system/bold>',width_in_chars=84},
        f:static_text{
            title='Subject Relight + Scene Relight + Creative Finishing • Offline • Batch',
            width_in_chars=84
        },

        f:group_box{
            title='1  RELIGHT MODE & CREATIVE PRESET',
            f:column{
                spacing=f:control_spacing(),
                f:row{
                    f:static_text{title='Mode',width_in_chars=23},
                    f:popup_menu{
                        value=View.bind('mode'),width_in_chars=34,
                        items={
                            {title='★ Full Auto — choose look per photo',value='auto'},
                            {title='◆ Preset Based — adaptive selected look',value='preset'},
                            {title='☼ Manual Creative — controlled virtual light',value='manual'},
                        }
                    }
                },
                f:row{
                    f:static_text{title='Creative Preset',width_in_chars=23},
                    f:popup_menu{
                        value=View.bind('preset'),width_in_chars=38,
                        items={
                            {title='Luxury Warm',value='luxury_warm'},
                            {title='Golden Hour',value='golden_hour'},
                            {title='Moody Indoor',value='moody_indoor'},
                            {title='Editorial Flash',value='editorial_flash'},
                            {title='Soft Bridal Glow',value='bridal_glow'},
                            {title='Dark Cinematic',value='dark_cinematic'},
                            {title='Cool Premium',value='cool_premium'},
                            {title='Sunset Drama',value='sunset_drama'},
                        }
                    }
                },
            }
        },

        f:group_box{
            title='2  SUBJECT LIGHT',
            f:column{
                spacing=f:control_spacing(),
                f:row{
                    f:static_text{title='Light Type',width_in_chars=23},
                    f:popup_menu{
                        value=View.bind('lightType'),width_in_chars=20,
                        items={
                            {title='Key Light',value='key'},
                            {title='Fill Light',value='fill'},
                            {title='Rim Light',value='rim'},
                            {title='Background Light',value='background'},
                        }
                    },
                    f:static_text{title='Kelvin',width_in_chars=9},
                    f:popup_menu{
                        value=View.bind('lightKelvin'),width_in_chars=18,
                        items={
                            {title='3200K Warm',value=3200},
                            {title='4300K Warm Neutral',value=4300},
                            {title='5500K Neutral',value=5500},
                            {title='6500K Cool',value=6500},
                            {title='9000K Blue',value=9000},
                        }
                    }
                },
                f:row{
                    f:static_text{title='Light X',width_in_chars=23},
                    f:edit_field{value=View.bind('lightX'),width_in_chars=8},
                    f:static_text{title='0 Left  •  50 Center  •  100 Right'}
                },
                f:row{
                    f:static_text{title='Light Y',width_in_chars=23},
                    f:edit_field{value=View.bind('lightY'),width_in_chars=8},
                    f:static_text{title='0 Top  •  50 Middle  •  100 Bottom'}
                },
                f:row{
                    f:static_text{title='Light Intensity',width_in_chars=23},
                    f:edit_field{value=View.bind('lightIntensity'),width_in_chars=8},
                    f:static_text{title='0–100'},
                    f:static_text{title='   Diffusion',width_in_chars=12},
                    f:edit_field{value=View.bind('lightDiffusion'),width_in_chars=8},
                },
                f:row{
                    f:static_text{title='Subject Light Strength',width_in_chars=23},
                    f:edit_field{value=View.bind('subjectStrength'),width_in_chars=8},
                    f:static_text{title='0–100'},
                    f:static_text{title='   Rim Strength',width_in_chars=12},
                    f:edit_field{value=View.bind('rimStrength'),width_in_chars=8},
                },
                f:checkbox{title='Face priority — protect skin and keep face lighting natural',value=View.bind('facePriority')},
            }
        },

        f:group_box{
            title='3  SCENE MOOD',
            f:column{
                spacing=f:control_spacing(),
                f:row{
                    f:static_text{title='Scene Mood Strength',width_in_chars=23},
                    f:edit_field{value=View.bind('sceneMood'),width_in_chars=8},
                    f:static_text{title='0–100'},
                },
                f:row{
                    f:static_text{title='Background Exposure',width_in_chars=23},
                    f:edit_field{value=View.bind('backgroundExposure'),width_in_chars=8},
                    f:static_text{title='-100 darker  •  +100 brighter'},
                },
                f:row{
                    f:static_text{title='Background Warm / Cool',width_in_chars=23},
                    f:edit_field{value=View.bind('backgroundTemp'),width_in_chars=8},
                    f:static_text{title='-100 cool  •  +100 warm'},
                },
                f:row{
                    f:static_text{title='Shadow Depth',width_in_chars=23},
                    f:edit_field{value=View.bind('shadowDepth'),width_in_chars=8},
                    f:static_text{title='0–100'},
                    f:static_text{title='   Light Spill',width_in_chars=12},
                    f:edit_field{value=View.bind('lightSpill'),width_in_chars=8},
                },
                f:row{
                    f:static_text{title='Subject Separation',width_in_chars=23},
                    f:edit_field{value=View.bind('separation'),width_in_chars=8},
                    f:static_text{title='Dark/cool background separation behind subject'},
                },
            }
        },

        f:group_box{
            title='4  CREATIVE FINISH',
            f:column{
                spacing=f:control_spacing(),
                f:row{
                    f:static_text{title='Creative Contrast',width_in_chars=23},
                    f:edit_field{value=View.bind('creativeContrast'),width_in_chars=8},
                    f:static_text{title='0–100'},
                    f:static_text{title='   Glow / Bloom',width_in_chars=12},
                    f:edit_field{value=View.bind('bloom'),width_in_chars=8},
                },
                f:row{
                    f:static_text{title='Highlight Softness',width_in_chars=23},
                    f:edit_field{value=View.bind('highlightSoftness'),width_in_chars=8},
                    f:static_text{title='0–100'},
                    f:static_text{title='   Vignette',width_in_chars=12},
                    f:edit_field{value=View.bind('vignette'),width_in_chars=8},
                },
                f:row{
                    f:static_text{title='Color Mood Strength',width_in_chars=23},
                    f:edit_field{value=View.bind('colorStrength'),width_in_chars=8},
                    f:static_text{title='0–100'},
                },
                f:row{
                    f:static_text{title='Original Light Retained',width_in_chars=23},
                    f:edit_field{value=View.bind('original'),width_in_chars=8},
                    f:static_text{title='0 = full V4 relight  •  100 = original'},
                },
            }
        },

        f:group_box{
            title='5  OUTPUT & BATCH',
            f:column{
                spacing=f:control_spacing(),
                f:row{
                    f:static_text{title='Quality',width_in_chars=23},
                    f:popup_menu{
                        value=View.bind('quality'),width_in_chars=30,
                        items={
                            {title='High — 4096 px analysis',value='high'},
                            {title='Standard — 2560 px analysis',value='standard'}
                        }
                    }
                },
                f:checkbox{title='Import and stack relit TIFF above original',value=View.bind('stack')},
                f:checkbox{title='Also save JPEG preview beside TIFF',value=View.bind('jpeg')},
                f:static_text{
                    title=count..' selected still photo(s). Every photo is analyzed individually. Originals are never overwritten.',
                    width_in_chars=80
                },
            }
        },
    }

    if Dialogs.presentModalDialog{
        title='AN AI Relight V4 — Creative Batch',
        contents=content,
        actionVerb='Render V4 Relight'
    }~='ok' then return nil end

    assert(p.mode=='auto' or p.mode=='preset' or p.mode=='manual','Invalid relight mode')
    assert(PRESETS[p.preset],'Invalid creative preset')
    assert(LIGHTS[p.lightType],'Invalid light type')
    assert(p.quality=='high' or p.quality=='standard','Invalid quality')

    return {
        mode=p.mode,preset=p.preset,
        lightType=p.lightType,
        lightX=number(p.lightX,0,100,'Light X'),
        lightY=number(p.lightY,0,100,'Light Y'),
        lightIntensity=number(p.lightIntensity,0,100,'Light intensity'),
        lightDiffusion=number(p.lightDiffusion,0,100,'Light diffusion'),
        lightKelvin=number(p.lightKelvin,1000,12000,'Kelvin'),
        rimStrength=number(p.rimStrength,0,100,'Rim strength'),
        facePriority=p.facePriority and 1 or 0,

        subjectStrength=number(p.subjectStrength,0,100,'Subject light strength'),
        sceneMood=number(p.sceneMood,0,100,'Scene mood strength'),
        backgroundExposure=number(p.backgroundExposure,-100,100,'Background exposure'),
        backgroundTemp=number(p.backgroundTemp,-100,100,'Background temperature'),
        shadowDepth=number(p.shadowDepth,0,100,'Shadow depth'),
        lightSpill=number(p.lightSpill,0,100,'Light spill'),
        separation=number(p.separation,0,100,'Subject separation'),

        creativeContrast=number(p.creativeContrast,0,100,'Creative contrast'),
        bloom=number(p.bloom,0,100,'Bloom'),
        highlightSoftness=number(p.highlightSoftness,0,100,'Highlight softness'),
        vignette=number(p.vignette,0,100,'Vignette'),
        colorStrength=number(p.colorStrength,0,100,'Color strength'),
        original=number(p.original,0,100,'Original lighting'),

        stack=p.stack,jpeg=p.jpeg,quality=p.quality
    }
end

local function preflight()
    local exe=Path.child(_PLUGIN.path,Engine.executable())
    assert(Files.exists(exe),'AN AI Relight V4 engine is missing. Run the V4 installer again.')
    return exe
end

local function safeStem(photo)
    local name=photo:getFormattedMetadata('fileName') or 'photo'
    local stem=name:gsub('%.[^%.]+$',''):gsub('[<>:"/\\|%?%*]','_')
    return stem~='' and stem or 'photo'
end

local function uniqueOutput(photo,suffix)
    local src=photo:getRawMetadata('path')
    assert(type(src)=='string' and src~='','Cannot determine source photo path.')
    local dir=Path.parent(src)
    local base=safeStem(photo)..'-ANAI-Relight-V4'
    local out=Path.child(dir,base..suffix)
    local n=2
    while Files.exists(out) do
        out=Path.child(dir,base..'-'..n..suffix)
        n=n+1
    end
    return out
end

local function renderPreview(photo,dir,progress,quality)
    local maxEdge=quality=='high' and 4096 or 2560
    local session=Export{photosToExport={photo},exportSettings={
        LR_exportServiceProvider='com.adobe.ag.export.file',
        LR_export_destinationType='specificFolder',
        LR_export_destinationPathPrefix=dir,
        LR_export_useSubfolder=false,
        LR_collisionHandling='rename',
        LR_format='JPEG',
        LR_jpeg_quality=1,
        LR_export_colorSpace='sRGB',
        LR_size_doConstrain=true,
        LR_size_doNotEnlarge=true,
        LR_size_resizeType='longEdge',
        LR_size_maxWidth=maxEdge,
        LR_size_maxHeight=maxEdge,
        LR_size_units='pixels',
        LR_outputSharpeningOn=false,
        LR_useWatermark=false,
        LR_reimportExportedPhoto=false,
        LR_renamingTokensOn=false,
        LR_minimizeEmbeddedMetadata=true,
        LR_removeLocationMetadata=true
    }}
    local rendered
    for _,rendition in session:renditions{stopIfCanceled=true,progressScope=progress} do
        local ok,path=rendition:waitForRender()
        assert(ok,'V4 source render failed: '..tostring(path))
        rendered=path
    end
    assert(rendered,'Lightroom returned no V4 source render.')
    return rendered
end

function M.run(ctx,catalog,photos,skipped,config,prefs,write)
    local engineExe=preflight()
    local root=Path.child(Path.getStandardFilePath('temp'),'ANAI-Relight-V4-'..UUID.generateUUID())
    assert(Files.createAllDirectories(root),'Cannot create V4 temporary folder.')

    local progress=Progress{title='AN AI Relight V4 - Creative Batch',functionContext=ctx}
    progress:setCancelable(true)
    ctx:addCleanupHandler(function() progress:done();Files.delete(root) end)

    local manifestPath=Path.child(root,'manifest.tsv')
    local resultsPath=Path.child(root,'results.tsv')
    local logPath=Path.child(root,'engine.log')
    local mf=assert(io.open(manifestPath,'wb'))
    assert(mf:write('ANAI_RELIGHT_V4_BATCH_1\n'))

    local outputById,sourceById={},{}
    local prepared,prepFailed=0,{}

    for i,photo in ipairs(photos) do
        if progress:isCanceled() then break end
        progress:setCaption('Preparing '..i..' / '..#photos..' - '..(photo:getFormattedMetadata('fileName') or 'Photo'))
        local dir=Path.child(root,tostring(i))
        Files.createAllDirectories(dir)

        local ok,err=Tasks.pcall(function()
            local input=renderPreview(photo,dir,progress,config.quality)
            local tif=uniqueOutput(photo,'.tif')
            local jpg=config.jpeg and uniqueOutput(photo,'.jpg') or ''
            assert(not input:find('[\r\n\t]') and not tif:find('[\r\n\t]') and not jpg:find('[\r\n\t]'),'Unsupported path character')
            outputById[i]=tif
            sourceById[i]=photo

            local row={
                i,input,tif,jpg,
                config.mode,config.preset,
                config.lightType,config.lightX,config.lightY,config.lightIntensity,config.lightDiffusion,config.lightKelvin,
                config.rimStrength,config.facePriority,
                config.subjectStrength,config.sceneMood,config.backgroundExposure,config.backgroundTemp,
                config.shadowDepth,config.lightSpill,config.separation,
                config.creativeContrast,config.bloom,config.highlightSoftness,config.vignette,config.colorStrength,config.original
            }
            assert(mf:write(table.concat(row,'\t')..'\n'))
            prepared=prepared+1
        end)

        if not ok then
            prepFailed[#prepFailed+1]=(photo:getFormattedMetadata('fileName') or ('Photo '..i))..': '..tostring(err)
        end
        progress:setPortionComplete(i,#photos*2)
        Tasks.yield()
    end

    mf:close()
    if progress:isCanceled() then progress:done();return end
    assert(prepared>0,'No photos could be prepared for AN AI Relight V4.')

    progress:setCaption('V4: matting, depth, subject light, scene mood and creative finish...')
    local command=Engine.quote(engineExe)..
        ' --manifest '..Engine.quote(manifestPath)..
        ' --results '..Engine.quote(resultsPath)..
        ' > '..Engine.quote(logPath)..' 2>&1'

    local status=Tasks.execute(Engine.wrap(command))
    assert(Files.exists(resultsPath),'V4 engine did not return results.\n'..(Files.readFile(logPath) or ''))
    if status~=0 then end

    local rows={}
    for line in (Files.readFile(resultsPath) or ''):gmatch('[^\r\n]+') do
        if line~='ANAI_RELIGHT_V4_RESULTS_1' then
            local id,state,message=line:match('^(%d+)\t(%a+)\t(.*)$')
            id=tonumber(id)
            assert(id and sourceById[id] and not rows[id],'Invalid V4 engine result')
            rows[id]={state=state,message=message}
        end
    end

    local imported,failed=0,#prepFailed
    local report={
        'AN AI Relight V4 — Creative Batch',
        os.date('%Y-%m-%d %H:%M:%S'),
        'Mode: '..config.mode..' | Preset: '..config.preset..
        ' | Subject: '..config.subjectStrength..' | Scene: '..config.sceneMood..
        ' | Original: '..config.original
    }

    for _,s in ipairs(prepFailed) do report[#report+1]='PREP ERROR - '..s end

    for i,photo in ipairs(photos) do
        local row=rows[i]
        if row and row.state=='ok' and Files.exists(outputById[i]) then
            local ok,err=Tasks.pcall(function()
                write(catalog,'AN AI Relight V4 - Import',function()
                    if config.stack then
                        catalog:addPhoto(outputById[i],photo,'above')
                    else
                        catalog:addPhoto(outputById[i])
                    end
                end)
            end)
            if ok then
                imported=imported+1
                report[#report+1]=(photo:getFormattedMetadata('fileName') or ('Photo '..i))..': OK - '..row.message
            else
                failed=failed+1
                report[#report+1]=(photo:getFormattedMetadata('fileName') or ('Photo '..i))..': IMPORT ERROR - '..tostring(err)
            end
        elseif outputById[i] then
            failed=failed+1
            report[#report+1]=(photo:getFormattedMetadata('fileName') or ('Photo '..i))..': ERROR - '..(row and row.message or 'Missing engine result')
        end
        progress:setPortionComplete(#photos+i,#photos*2)
        Tasks.yield()
    end

    progress:done()
    report[#report+1]='Rendered/imported: '..imported
    report[#report+1]='Failed: '..failed
    report[#report+1]='Skipped videos: '..skipped
    prefs.lastV4RelightReport=table.concat(report,'\n')
    Dialogs.message('AN AI Relight V4',prefs.lastV4RelightReport,'info')
end

return M
