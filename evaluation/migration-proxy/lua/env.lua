local _M = {}

local upstream = os.getenv("DEFAULT_UPSTREAM") or "10.131.36.31"

function _M.get_upstream()
    return upstream
end

function _M.set_upstream(value)
    upstream = value
end

return _M