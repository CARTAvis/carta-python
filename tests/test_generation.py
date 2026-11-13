import pytest

from carta.constants import JobStatus, Moment as M, MomentMask as MM, RegionType as RT, SpectralSystem as SS, SpectralType as ST, SpectralUnit as SU
from carta.generation import CartaJobFailed, GenerationJob, MomentImages, MomentJob, PvImages, PvJob, channel_settings
from carta.image import Image
from carta.region import Region
from carta.session import Session
from carta.util import CartaBadResponse, CartaValidationFailed

# FIXTURES


@pytest.fixture
def moments(image):
    return MomentImages(image)


@pytest.fixture
def session_call_action(session, mock_call_action):
    return mock_call_action(session)


@pytest.fixture
def region(image, mocker):
    def func(region_type, region_id=3, owner=None):
        region = Region(image.regions if owner is None else owner.regions, region_id)
        mocker.patch.object(Region, "region_type", new_callable=mocker.PropertyMock, return_value=region_type)
        return region
    return func


def job_states(*states):
    """Return the states of a job that the frontend returns in turn."""
    return [{"status": "running", "progress": 0, "images": []}, *states]


# TESTS


@pytest.mark.parametrize("args,expected", [
    ([None, None, None, None, None], {}),
    ([None, None, None, None, (2, 7)], {"channels": {"min": 2, "max": 7}}),
    ([(1.5, 2.5), None, None, None, None], {"spectralRange": {"min": 1.5, "max": 2.5}}),
    ([(-10, 20), ST.VRAD, None, None, None], {"spectralRange": {"min": -10, "max": 20, "type": ST.VRAD}}),
    ([(-10, 20), ST.VRAD, SU.MS, SS.BARY, None], {"spectralRange": {"min": -10, "max": 20, "type": ST.VRAD, "unit": SU.MS, "system": SS.BARY}}),
    ([(230.5, 230.6), None, SU.GHZ, None, None], {"spectralRange": {"min": 230.5, "max": 230.6, "unit": SU.GHZ}}),
])
def test_channel_settings(args, expected):
    assert channel_settings(*args) == expected


@pytest.mark.parametrize("args,message", [
    ([(1, 2), None, None, None, (1, 2)], "not both"),
    ([None, ST.VRAD, None, None, None], "needs a spectral range"),
    ([(1, 2), ST.VRAD, SU.GHZ, None, None], "GHz is not a unit of the spectral type VRAD"),
])
def test_channel_settings_invalid(args, message):
    with pytest.raises(CartaValidationFailed) as e:
        channel_settings(*args)
    assert message in str(e.value)


def test_generate_over_whole_image(moments, session_call_action):
    session_call_action.return_value = 4
    job = moments.generate([M.INTEGRATED, M.MAX])
    session_call_action.assert_called_with("imageGenerationJobs.startMoments", 0, {"moments": [M.INTEGRATED, M.MAX], "mask": MM.NONE, "keep": True}, response_expected=True)
    assert isinstance(job, MomentJob)
    assert job.job_id == 4


def test_generate_with_all_settings(moments, session_call_action, region):
    session_call_action.return_value = 5
    moments.generate([M.WEIGHTED_COORD], region=region(RT.ELLIPSE, 7), spectral_range=(-10, 20), spectral_type=ST.VRAD, mask=MM.INCLUDE, pixel_range=(0.01, 1), keep=False)
    session_call_action.assert_called_with("imageGenerationJobs.startMoments", 0, {
        "moments": [M.WEIGHTED_COORD],
        "mask": MM.INCLUDE,
        "keep": False,
        "regionId": 7,
        "pixelRange": {"min": 0.01, "max": 1},
        "spectralRange": {"min": -10, "max": 20, "type": ST.VRAD},
    }, response_expected=True)


@pytest.mark.parametrize("region_type", [RT.LINE, RT.POINT, RT.ANNRECTANGLE])
def test_generate_needs_closed_region(moments, session_call_action, region, region_type):
    with pytest.raises(CartaValidationFailed) as e:
        moments.generate([M.MAX], region=region(region_type))
    assert "rectangle, ellipse or polygon region" in str(e.value)
    session_call_action.assert_not_called()


def test_generate_needs_region_of_same_image(moments, session, session_call_action, region):
    with pytest.raises(CartaValidationFailed) as e:
        moments.generate([M.MAX], region=region(RT.RECTANGLE, owner=Image(session, 1)))
    assert "does not belong to this image" in str(e.value)
    session_call_action.assert_not_called()


def test_generate_needs_region_of_same_session(moments, session_call_action, region):
    other_session = Session(0, None)
    with pytest.raises(CartaValidationFailed) as e:
        moments.generate([M.MAX], region=region(RT.RECTANGLE, owner=Image(other_session, 0)))
    assert "does not belong to this image" in str(e.value)
    session_call_action.assert_not_called()


def test_generate_sends_keep_as_boolean(moments, session_call_action):
    moments.generate([M.MAX], keep=0)
    assert session_call_action.call_args.args[2]["keep"] is False


@pytest.mark.parametrize("kwargs", [
    {"moments": []},
    {"moments": [13]},
    {"moments": [M.MAX], "mask": MM.INCLUDE},
    {"moments": [M.MAX], "channels": (-1, 2)},
    {"moments": [M.MAX], "channels": (1, 2, 3)},
    {"moments": [M.MAX], "spectral_range": (1, 2), "channels": (1, 2)},
])
def test_generate_invalid(moments, session_call_action, kwargs):
    with pytest.raises(CartaValidationFailed):
        moments.generate(**kwargs)
    session_call_action.assert_not_called()


def test_images_leaves_out_closed_images(moments, image, session, mocker):
    get_value = mocker.patch.object(image, "get_value", return_value=[3, 4, 5])
    session_get_value = mocker.patch.object(session, "get_value", return_value=[0, 3, 5])
    images = moments.images
    get_value.assert_called_with("momentImages", return_path="frameInfo.fileId")
    session_get_value.assert_called_with("frames", return_path="frameInfo.fileId")
    assert [i.image_id for i in images] == [3, 5]


def test_close_all(moments, image, session, mocker):
    mocker.patch.object(image, "get_value", return_value=[3, 4])
    mocker.patch.object(session, "get_value", return_value=[0, 3, 4])
    close = mocker.patch.object(Image, "close")
    moments.close_all()
    assert close.call_count == 2


def test_job_state(session, session_call_action):
    job = GenerationJob(session, 2)
    session_call_action.return_value = {"status": "failed", "progress": 0, "images": [], "error": "the image was closed"}
    assert job.status == JobStatus.FAILED
    assert job.progress == 0
    assert job.error == "the image was closed"
    session_call_action.assert_called_with("imageGenerationJobs.getJob", 2, response_expected=True)


def test_job_cancel(session, session_call_action):
    GenerationJob(session, 2).cancel()
    session_call_action.assert_called_with("imageGenerationJobs.cancelJob", 2)


def test_moment_job_wait(session, session_call_action, mocker):
    sleep = mocker.patch("carta.generation.time.sleep")
    session_call_action.side_effect = job_states({"status": "done", "progress": 1, "images": [{"fileId": 3, "moment": 1}, {"fileId": 4, "moment": 9}]})
    images = MomentJob(session, 2).wait(poll_interval=0.5)
    sleep.assert_called_once_with(0.5)
    assert list(images) == [M.INTEGRATED, M.MAX]
    assert [i.image_id for i in images.values()] == [3, 4]


@pytest.mark.parametrize("state,message", [
    ({"status": "failed", "progress": 0, "images": [], "error": "the region was deleted"}, "The job failed: the region was deleted."),
    ({"status": "cancelled", "progress": 0, "images": []}, "The job was cancelled."),
])
def test_job_wait_raises(session, session_call_action, mocker, state, message):
    mocker.patch("carta.generation.time.sleep")
    session_call_action.side_effect = job_states(state)
    with pytest.raises(CartaJobFailed) as e:
        MomentJob(session, 2).wait()
    assert str(e.value) == message


def test_job_wait_invalid_interval(session, session_call_action):
    with pytest.raises(CartaValidationFailed):
        GenerationJob(session, 2).wait(poll_interval=0)
    session_call_action.assert_not_called()


def test_generate_asks_for_each_moment_once(moments, session_call_action):
    moments.generate([M.MAX, M.INTEGRATED, M.MAX])
    assert session_call_action.call_args.args[2]["moments"] == [M.MAX, M.INTEGRATED]


@pytest.mark.parametrize("state,message", [
    ({"status": "done", "progress": 1, "images": [{"fileId": 3}]}, "could not tell which moment"),
    ({"status": "paused", "progress": 0, "images": []}, "unknown status: paused"),
])
def test_moment_job_wait_bad_response(session, session_call_action, mocker, state, message):
    mocker.patch("carta.generation.time.sleep")
    session_call_action.side_effect = job_states(state)
    with pytest.raises(CartaBadResponse) as e:
        MomentJob(session, 2).wait()
    assert message in str(e.value)


# PV IMAGES


@pytest.fixture
def pv(image):
    return PvImages(image)


def test_pv_generate(pv, session_call_action, region):
    session_call_action.return_value = 6
    job = pv.generate(region(RT.POLYLINE, 8), width=3, channels=(2, 20), reverse=True, keep=False)
    session_call_action.assert_called_with("imageGenerationJobs.startPv", 0, {"regionId": 8, "width": 3, "reverse": True, "keep": False, "channels": {"min": 2, "max": 20}}, response_expected=True)
    assert isinstance(job, PvJob)
    assert job.job_id == 6


def test_pv_generate_defaults_and_spectral_range(pv, session_call_action, region):
    pv.generate(region(RT.LINE), spectral_range=(230.51, 230.57), unit=SU.GHZ)
    session_call_action.assert_called_with("imageGenerationJobs.startPv", 0, {"regionId": 3, "width": 1, "reverse": False, "keep": True, "spectralRange": {"min": 230.51, "max": 230.57, "unit": SU.GHZ}}, response_expected=True)


@pytest.mark.parametrize("region_type", [RT.RECTANGLE, RT.ANNLINE, RT.POINT])
def test_pv_generate_needs_line_region(pv, session_call_action, region, region_type):
    with pytest.raises(CartaValidationFailed) as e:
        pv.generate(region(region_type))
    assert "line or polyline region" in str(e.value)
    session_call_action.assert_not_called()


@pytest.mark.parametrize("width", [0, 21, 1.5])
def test_pv_generate_invalid_width(pv, session_call_action, region, width):
    with pytest.raises(CartaValidationFailed):
        pv.generate(region(RT.LINE), width=width)
    session_call_action.assert_not_called()


def test_pv_images(pv, image, session, mocker):
    get_value = mocker.patch.object(image, "get_value", return_value=[7, 8])
    mocker.patch.object(session, "get_value", return_value=[0, 8])
    assert [i.image_id for i in pv.images] == [8]
    get_value.assert_called_with("pvImages", return_path="frameInfo.fileId")


@pytest.mark.parametrize("images,expected", [
    ([{"fileId": 9}], 9),
    ([], None),
])
def test_pv_job_wait(session, session_call_action, mocker, images, expected):
    mocker.patch("carta.generation.time.sleep")
    session_call_action.side_effect = job_states({"status": "done", "progress": 1, "images": images})
    result = PvJob(session, 2).wait()
    assert (result.image_id if result else None) == expected


def test_pv_generate_needs_region_of_same_image(pv, session, session_call_action, region):
    with pytest.raises(CartaValidationFailed) as e:
        pv.generate(region(RT.LINE, owner=Image(session, 1)))
    assert "does not belong to this image" in str(e.value)
    session_call_action.assert_not_called()


def test_pv_generate_needs_region_of_same_session(pv, session_call_action, region):
    with pytest.raises(CartaValidationFailed) as e:
        pv.generate(region(RT.LINE, owner=Image(Session(0, None), 0)))
    assert "does not belong to this image" in str(e.value)
    session_call_action.assert_not_called()


def test_pv_generate_sends_booleans(pv, session_call_action, region):
    pv.generate(region(RT.LINE), reverse=1, keep=0)
    settings = session_call_action.call_args.args[2]
    assert settings["reverse"] is True
    assert settings["keep"] is False
