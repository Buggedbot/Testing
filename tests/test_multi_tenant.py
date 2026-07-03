from self_healing_locator import Healer
from self_healing_locator.store import LocatorSpec


def test_client_id_isolates_store_paths(tmp_path):
    healer_a = Healer(client_id="acme-corp", base_dir=tmp_path / "locators")
    healer_b = Healer(client_id="globex", base_dir=tmp_path / "locators")

    healer_a.store.put(LocatorSpec(name="save_btn", selector="#a-save", fingerprint={}))
    healer_b.store.put(LocatorSpec(name="save_btn", selector="#b-save", fingerprint={}))

    assert healer_a.store.path == tmp_path / "locators" / "acme-corp" / "locators.yaml"
    assert healer_b.store.path == tmp_path / "locators" / "globex" / "locators.yaml"

    # Reloading each client's store must never see the other client's data.
    reloaded_a = Healer(client_id="acme-corp", base_dir=tmp_path / "locators")
    reloaded_b = Healer(client_id="globex", base_dir=tmp_path / "locators")
    assert reloaded_a.store.get("save_btn").selector == "#a-save"
    assert reloaded_b.store.get("save_btn").selector == "#b-save"


def test_client_id_and_store_path_are_mutually_exclusive(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        Healer(store_path=tmp_path / "locators.yaml", client_id="acme-corp")
