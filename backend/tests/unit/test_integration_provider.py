import pytest

from app.domains.integrations.provider import FakeIdentityProvider, ProviderPermanentError


@pytest.mark.asyncio
async def test_fake_identity_provider_supports_incremental_pages() -> None:
    provider = FakeIdentityProvider()

    first = await provider.pull(
        {"api_token": "sandbox-token"},
        "applications",
        None,
        {},
    )
    second = await provider.pull(
        {"api_token": "sandbox-token"},
        "applications",
        first.next_cursor,
        {},
    )
    complete = await provider.pull(
        {"api_token": "sandbox-token"},
        "applications",
        second.next_cursor,
        {},
    )

    assert [record.external_id for record in first.records] == ["app-notion"]
    assert [record.external_id for record in second.records] == ["app-figma"]
    assert complete.records == []
    assert complete.next_cursor == "page-2"


@pytest.mark.asyncio
async def test_fake_identity_provider_can_fail_a_sandbox_page() -> None:
    provider = FakeIdentityProvider()

    with pytest.raises(ProviderPermanentError):
        await provider.pull(
            {"api_token": "sandbox-token"},
            "applications",
            "page-1",
            {"fail_on_page": 2},
        )
