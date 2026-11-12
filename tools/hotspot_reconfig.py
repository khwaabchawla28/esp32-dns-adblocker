import asyncio
from winsdk.windows.networking.connectivity import NetworkInformation
from winsdk.windows.networking.networkoperators import (
    NetworkOperatorTetheringManager,
    NetworkOperatorTetheringAccessPointConfiguration,
    TetheringWiFiBand,
)

async def main():
    profile = NetworkInformation.get_internet_connection_profile()
    print('internet profile:', profile.profile_name if profile else None)
    mgr = NetworkOperatorTetheringManager.create_from_connection_profile(profile)
    print('state before:', mgr.tethering_operational_state)

    # stop while reconfiguring
    if mgr.tethering_operational_state == 1:
        r = await mgr.stop_tethering_async()
        print('stop status:', r.status)

    cfg = NetworkOperatorTetheringAccessPointConfiguration()
    cfg.ssid = 'HermesTest'
    cfg.passphrase = 'adblock1234'
    cfg.band = TetheringWiFiBand.TWO_POINT_FOUR_GIGAHERTZ
    r = await mgr.configure_access_point_async(cfg)
    print('configure status:', getattr(r, 'status', r))

    r = await mgr.start_tethering_async()
    print('start status:', r.status)

    mgr2 = NetworkOperatorTetheringManager.create_from_connection_profile(profile)
    cfg2 = mgr2.get_current_access_point_configuration()
    print('FINAL SSID:', repr(cfg2.ssid))
    print('FINAL PASS:', repr(cfg2.passphrase))
    print('FINAL BAND:', cfg2.band, '(0=2.4GHz)')
    print('FINAL STATE:', mgr2.tethering_operational_state)

asyncio.run(main())
