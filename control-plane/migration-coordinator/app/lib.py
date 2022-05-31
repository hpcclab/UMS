import asyncio


def get_information():
    with open('/etc/os-release') as f:
        return f.read()


async def gather(fn_list):
    return await asyncio.gather(*fn_list)
