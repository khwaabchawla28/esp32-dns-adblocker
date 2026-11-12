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
    if profile is None:
        print('NO_INTERNET_PROFILE')
        return
    mgr = NetworkOperatorTetheringManager.create_from_connection_profile(profile)
    print('clients:', mgr.client_count, 'state:', mgr.tethering_operational_state)

    cfg = NetworkOperatorTetheringAccessPointConfiguration()
    cfg.ssid = 'HermesTest'
    cfg.passphrase = 'adblock1234'
    try:
        cfg.band = TetheringWiFiBand.TWO_POINT_FOUR_GIGAHERTZ
        print('band set to 2.4 GHz')
    except Exception as e:
        print('band set failed (ok if API lacks it):', e)
    try:
        mgr.configure_access_point(cfg)
        print('configured SSID:', cfg.ssid, 'band:', cfg.band)
    except Exception as e:
        print('CONFIGURE_FAILED:', e)

    state = mgr.tethering_operational_state
    print('state before start:', state)
    if state != 1:  # 1 = TetheringOperationalState.ON
        try:
            res = await mgr.start_tethering_async()
            print('start status:', res.status)
        except Exception as e:
            print('START_FAILED:', e)
    mgr = NetworkOperatorTetheringManager.create_from_connection_profile(profile)
    print('state after:', mgr.tethering_operational_state, 'clients:', mgr.client_count)

asyncio.run(main())
