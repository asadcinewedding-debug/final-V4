local App = import 'LrApplication'
local Context = import 'LrFunctionContext'
local Dialogs = import 'LrDialogs'
local Prefs = import 'LrPrefs'
local Tasks = import 'LrTasks'

local prefs = Prefs.prefsForPlugin()
local M = {}
local busy = false

local function chosen()
    local catalog = App.activeCatalog()
    if not catalog:getTargetPhoto() then error('Select the photos you want to relight first.') end
    local photos, skipped = {}, 0
    for _, photo in ipairs(catalog:getTargetPhotos()) do
        if photo:getRawMetadata('fileFormat') ~= 'VIDEO' then
            photos[#photos + 1] = photo
        else
            skipped = skipped + 1
        end
    end
    if #photos == 0 then error('Please select at least one still photo.') end
    return catalog, photos, skipped
end

local function write(catalog, name, fn)
    local executed = false
    catalog:withWriteAccessDo(name, function()
        fn()
        executed = true
    end, { timeout = 20 })
    if not executed then error('The Lightroom catalog is busy. Wait and try again.') end
end

function M.relight(ctx)
    local catalog, photos, skipped = chosen()
    local Relighting = require 'Relighting'
    local config = Relighting.configure(ctx, #photos)
    if config then
        Relighting.run(ctx, catalog, photos, skipped, config, prefs, write)
    end
end

function M.launch(action)
    if busy then
        Dialogs.message('AN AI Relight V4','A relight operation is already running.','warning')
        return
    end
    busy = true
    Tasks.startAsyncTask(function()
        local ok, err = Tasks.pcall(function()
            Context.callWithContext('AN AI Relight V4', function(ctx)
                assert(M[action], 'Unknown action')(ctx)
            end)
        end)
        busy = false
        if not ok then Dialogs.message('AN AI Relight V4', tostring(err), 'critical') end
    end)
end

return M
