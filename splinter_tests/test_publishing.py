import pytest

from topobank.manager.tests.utils import SurfaceFactory, TopographyFactory
from splinter_tests.utils import goto_select_page, goto_publications_page, press_properties_for_item_by_name


def press_yes_publish(browser):
    publish_btn = browser.find_by_name('save').first
    publish_btn.click()


def press_permissions(browser):
    browser.links.find_by_partial_text("Permissions").first.click()


@pytest.mark.django_db
def test_publishing_form(user_alice_logged_in, user_bob, handle_usage_statistics):

    browser, user_alice = user_alice_logged_in

    #
    # Generate surface with topography for Alice.
    #
    surface_name = "First published surface"

    surface = SurfaceFactory(creator=user_alice, name=surface_name)
    # a topography is added later

    #
    # When going to the "Published surfaces tab", nothing is listed
    #
    goto_publications_page(browser)
    assert browser.is_text_present("You haven't published any surfaces yet.")


    #
    # Alice opens properties for the surface
    #
    goto_select_page(browser)
    press_properties_for_item_by_name(browser, surface_name)

    #
    # Alice presses "Publish" button. The extra "Publish surface ..." tab opens.
    #
    assert browser.is_text_present("Publish")
    publish_btn = browser.links.find_by_partial_text("Publish")
    publish_btn.click()

    #
    # Since no topography is available for the surface, a hint is shown
    #
    assert browser.is_text_present("This surface has no topographies yet")

    #
    # We add a topography and reload
    #
    TopographyFactory(surface=surface)
    browser.reload()

    #
    # There are three licenses for selection. Alice chooses the "CC BY-SA"
    # license
    #
    browser.choose('license', 'ccbysa-4.0')

    #
    # Alice presses Publish. She didn't check the checkboxes, we are still on page
    #
    press_yes_publish(browser)

    assert len(browser.find_by_name("save")) > 0

    #
    # Alice checks one checkbox, the other is still needed
    #
    browser.find_by_id('id_ready').first.click()

    press_yes_publish(browser)
    assert len(browser.find_by_name("save")) > 0

    # Alice checks the second and tries again to publish.
    # The extra tab is closed and Alice is taken
    # to the list of published surfaces.
    browser.find_by_id('id_agreed').first.click()

    press_yes_publish(browser)
    assert len(browser.find_by_name("save")) == 0
    assert browser.is_text_present("Surfaces published by you", wait_time=1)

    # Here the published surface is listed.
    # Alice presses the link and enters the property page for the surface.
    assert browser.is_text_present(surface_name)
    browser.find_by_css('td').find_by_text(surface_name).click()

    #
    # Here a "published by you" badge is shown.
    #
    assert browser.is_text_present("published by you")

    # She opens the permissions and sees that Everyone has read permissions
    # and nothing else.
    # The individual names are NOT listed.
    press_permissions(browser)

    assert not browser.is_text_present(user_bob.name)  # we don't want to list all names here
    assert browser.is_text_present("Everyone")


@pytest.mark.django_db
def test_see_published_by_others(user_alice_logged_in, user_bob, handle_usage_statistics):

    browser, user_alice = user_alice_logged_in

    #
    # User Bob publishes a surface
    #
    surface = SurfaceFactory(creator=user_bob)
    TopographyFactory(surface=surface)
    surface.publish('cc0')

    # Alice filters for published surfaces - enters
    # "Select" tab and chooses "Only published surfaces"
    #

    # Bobs surface is visible. She opens the properties and sees
    # the "published by Bob" badge.

    # She opens the permissions and sees that Everyone has read permissions
    # and nothing else.
    # The individual names are NOT listed.
    press_permissions(browser)

    assert not browser.is_text_present(user_alice.name)  # we don't want to list all names here
    assert not browser.is_text_present(user_bob.name)  # we don't want to list all names here
    assert not browser.is_text_present("Everyone")


