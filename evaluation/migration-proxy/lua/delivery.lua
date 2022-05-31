local http = require("resty.http")
local env = require("env")

local uri = ngx.var.uri

local http_client = http.new()
ngx.log(ngx.STDERR, "http://" .. env.get_upstream() .. uri)
local res, err = http_client:request_uri("http://" .. env.get_upstream() .. uri)

if res then
    ngx.log(ngx.STDERR, res.status)
end
ngx.log(ngx.STDERR, err)

if err then
    error(err)
end

if res.status == 301 then
    ngx.log(ngx.STDERR, res.headers.Location)
    env.set_upstream(res.headers.Location)
    ngx.log(ngx.STDERR, "http://" .. env.get_upstream() .. uri)
    res, err = http_client:request_uri("http://" .. env.get_upstream() .. uri)

    if res then
        ngx.log(ngx.STDERR, res.status)
    end
    ngx.log(ngx.STDERR, err)

    if err then
        error(err)
    end
end

ngx.status = res.status
ngx.print(res.body)