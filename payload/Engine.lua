local M={}
function M.executable()
    return 'engine/relight_engine.exe'
end
function M.quote(s)
    assert(not s:find('[\r\n%z]'),'Engine path contains unsupported control characters')
    assert(not s:find('[%%!"]'),'Engine path contains unsupported Windows characters (% ! or quotes). Use a plain path.')
    return '"'..s..'"'
end
function M.wrap(command) return '"'..command..'"' end
return M
