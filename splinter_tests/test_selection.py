import pytest

from topobank.manager.tests.utils import SurfaceFactory, TopographyFactory, TagModelFactory
from topobank.manager.models import Surface, Topography, TagModel

@pytest.fixture(scope='function')
def items_for_selection(db, user_alice):

    tag1 = TagModelFactory()
    tag2 = TagModelFactory()

    surface1 = SurfaceFactory(creator=user_alice)
    topo1a = TopographyFactory(surface=surface1)
    topo1b = TopographyFactory(surface=surface1, tags=[tag1, tag2])

    surface2 = SurfaceFactory(creator=user_alice, tags=[tag1])
    topo2a = TopographyFactory(surface=surface2)

    return dict(
        tags=[tag1, tag2],
        surfaces=[surface1, surface2],
        topographies=[topo1a, topo1b, topo2a]
    )


def checkbox_for_item_by_name(browser, name):
    node_elems = browser.find_by_xpath(f'//td//span[text()="{name}"]/..')
    checkbox = node_elems.find_by_css('span.fancytree-checkbox').first
    return checkbox


def select_item_by_name(browser, name):
    checkbox = checkbox_for_item_by_name(browser, name)
    checkbox.check()


def is_in_basket(browser, name):
    badges = browser.find_by_id('basket').find_by_css('span.badge')
    # find_by_text does not work as expected and a nested second find_by_xpath not search from
    # previously found node as expected, so this is a workaround

    texts = [b.text for b in badges]

    return name in texts


@pytest.mark.django_db
def test_deselect_all(browser, user_alice_logged_in, items_for_selection):

    #
    # navigate to select page and select sth.
    #
    select_link = browser.find_link_by_partial_text('Select')
    select_link.click()

    cb = checkbox_for_item_by_name(browser, 'surface-0')
    cb.check()

    # now we have a basket item
    assert is_in_basket(browser, 'surface-0')

    # pressing unselect
    browser.click_link_by_id('unselect-all')

    # time.sleep(1)

    # now the basket item is no longer there
    assert not is_in_basket(browser, 'surface-0')

    browser.quit()


@pytest.mark.django_db
def test_select_page_size(browser, user_alice_logged_in):

    # create a lot of surfaces
    for i in range(11):
        SurfaceFactory(creator=user_alice_logged_in)

    #
    # navigate to select page
    #
    select_link = browser.find_link_by_partial_text('Select')
    select_link.click()

    #
    # pagination should have 2 pages
    #
    pagination = browser.find_by_id("pagination")

    # there should be 4 items: previous, 1, 2, next
    assert browser.is_text_present("Next", wait_time=1)

    page_items = pagination.find_by_css(".page-item")

    assert len(page_items) == 4

    assert page_items[0].text == "Previous"
    assert page_items[1].text == "1"
    assert page_items[2].text == "2"
    assert page_items[3].text == "Next"

    # page size should show "10"
    page_size_select = browser.find_by_id("page-size-select")
    assert page_size_select.find_by_css(".selected").first.text == "10"

    # footer should show total number
    assert browser.is_text_present("Showing 10 surfaces out of 11")

    # press "Next"
    page_items[3].click()

    # now footer shows different text
    assert browser.is_text_present("Showing 1 surfaces out of 11", wait_time=1)

    # select page size 25
    page_size_25_option = page_size_select.find_by_css('option')[1]
    assert page_size_25_option.text == "25"
    page_size_25_option.click()

    # now there is only one page
    assert browser.is_text_present("Next", wait_time=1)
    assert browser.is_text_present("Showing 11 surfaces out of 11", wait_time=1)

    pagination = browser.find_by_id("pagination")
    page_items = pagination.find_by_css(".page-item")

    assert len(page_items) == 3

    assert page_items[0].text == "Previous"
    assert page_items[1].text == "1"
    assert page_items[2].text == "Next"















