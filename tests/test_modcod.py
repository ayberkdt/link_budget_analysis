import pytest
from src.modcod import select_best_modcod, esn0_from_cn0_db

def test_esn0_from_cn0_db():
    # 36 MHz bandwidth, 0.20 rolloff -> 30 Msps
    # If C/N0 = 80 dB-Hz, Es/N0 = 80 - 10*log10(30e6) = 80 - 74.771 = 5.228 dB
    esn0 = esn0_from_cn0_db(cn0_dbhz=80.0, bandwidth_hz=36e6, rolloff_factor=0.20)
    assert pytest.approx(esn0, 0.01) == 5.228

def test_select_best_modcod_clear_sky():
    # For a high Es/N0 like 10.0 dB and 1 dB implementation margin (usable = 9.0 dB)
    # The highest MODCOD <= 9.0 is 16APSK 2/3 (requires 8.97)
    selection = select_best_modcod(
        available_esn0_db=10.0,
        bandwidth_hz=36e6,
        rolloff_factor=0.20,
        implementation_margin_db=1.0
    )
    assert selection.selected is not None
    assert selection.selected.name == "16APSK 2/3"
    assert selection.selected.required_esn0_db == 8.97
    # 30 Msps * 2.637201 bps/Hz = ~79.1 Mbps
    assert pytest.approx(selection.net_throughput_bps / 1e6, 0.1) == 79.1

def test_select_best_modcod_rain_fade():
    # For a very low Es/N0 like 1.0 dB and 1 dB implementation margin (usable = 0.0 dB)
    # The highest MODCOD <= 0.0 is QPSK 2/5 (requires -0.30)
    selection = select_best_modcod(
        available_esn0_db=1.0,
        bandwidth_hz=36e6,
        rolloff_factor=0.20,
        implementation_margin_db=1.0
    )
    assert selection.selected is not None
    assert selection.selected.name == "QPSK 2/5"

def test_select_best_modcod_outage():
    # Usable = -4.0 dB. Even QPSK 1/4 needs -2.35 dB. Should return None.
    selection = select_best_modcod(
        available_esn0_db=-3.0,
        bandwidth_hz=36e6,
        rolloff_factor=0.20,
        implementation_margin_db=1.0
    )
    assert selection.selected is None
    assert selection.net_throughput_bps == 0.0
