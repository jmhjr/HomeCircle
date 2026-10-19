"""Select fresh-onboarding profiles without changing legacy report clients."""

ANDROID_CLIENT_INFO = (
    '<Pixel 8><Android; 14; UQ1A.240205.004>'
    '<com.apple.AuthKit/1 (com.apple.android.music/4.9.6)>'
)


IOS_CLOUDKIT_CLIENT_INFO = (
    '<iPhone5,3> <iPhone OS;9.0.1;13A404> '
    '<com.apple.cloudkit.CloudKitDaemon/479 (com.apple.cloudd/479)>'
)

NATIVE_CLIENT_INFO = (
    '<Mac14,2> <macOS;15.7.5;24G624> '
    '<com.apple.AuthKit/1 (com.apple.akd/1.0)>'
)


def configure_account(account):
    """Restore the selected policy; unmarked saved report sessions keep their path."""
    from ._vendor_findmy.reports.anisette import CLIENT_IDENTITY, DeviceIdentity

    provider = getattr(account, '_anisette', None)
    if getattr(provider, '_homecircle_mac', False):
        # The per-account Mac machine is serialized with its passwordless vault.
        # Never relabel it as the older Android or Windows diagnostic profiles.
        from ._findmy_runtime.provider import CLIENT_INFO
        from ._findmy_runtime.onboarding import bind_account

        if (account.local_user_uuid, account.device_uuid) != (
            provider.local_user_uuid, provider.device_uuid,
        ):
            raise ValueError('Find My identity mismatch')
        account.gsa_client_info = CLIENT_INFO
        account.reuse_recent_pet = False
        bind_account(account)
        return account
    if getattr(account, 'endpoint_policy', None) is not None:
        if provider is not None:
            provider._bounded_onboarding = True
        if provider is not None and getattr(provider, '_is_new_session', False):
            # The native Android ADI engine retains its own provisioning IDs.
            # Service declarations are selected separately by endpoint policy.
            # A restored provider keeps its original VM profile and identity.
            provider._native_client_info = NATIVE_CLIENT_INFO
            provider._identity = CLIENT_IDENTITY
            provider._serial = '0'
        account.reuse_recent_pet = True
        return account
    if provider is not None:
        provider._native_client_info = ANDROID_CLIENT_INFO
        provider._identity = DeviceIdentity(
            model='Pixel 8', os_name='Android', os_version='14',
            os_build='UQ1A.240205.004', cfnetwork='1408.0.4', darwin='22.5.0',
        )
    account.reuse_recent_pet = True
    account.gsa_client_info = ANDROID_CLIENT_INFO
    account.cloudkit_client_info = IOS_CLOUDKIT_CLIENT_INFO
    return account
