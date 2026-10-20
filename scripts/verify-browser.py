"""Verify offline controls, URL presets, saved states and actual MuWeb composition."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import Frame, Page, expect, sync_playwright


def ready(surface: Page | Frame) -> None:
    """Wait for an initialized application with a completely drawn formula.

    Args:
        surface: Application page or opaque sandbox frame.
    """
    expect(surface.locator('#app[data-ready="true"]')).to_be_visible(timeout=30000)
    expect(surface.locator('#function-curve')).to_have_count(1)
    assert not surface.locator('#notice').inner_text()


def slider(surface: Page | Frame, key: str, value: float) -> None:
    """Exercise the production slider event path.

    Args:
        surface: Application page or sandbox frame.
        key: Active parameter identifier.
        value: Requested slider value within its range.
    """
    surface.locator(f'#slider-{key}').evaluate('(el,value)=>{el.value=value;el.dispatchEvent(new Event("input",{bubbles:true}));}', value)


def app_frame(page: Page) -> Frame:
    """Find a production application frame after the host has initialized it.

    Args:
        page: Parent browser page containing one visible application frame.
    """
    page.wait_for_function('Array.from(document.querySelectorAll("iframe")).some(frame=>frame.src.startsWith("blob:"))')
    for _ in range(100):
        sources = page.locator('iframe:visible').evaluate_all('(frames)=>frames.map(frame=>frame.src)')
        for frame in page.frames[1:]:
            if frame.url in sources and frame.locator('#app').count():
                ready(frame)
                return frame
        page.wait_for_timeout(100)
    raise AssertionError('No application frame')


def main() -> None:
    """Run deterministic browser interactions with all network requests blocked."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--only', choices=('standalone', 'host', 'pyhtml', 'failures'))
    parser.add_argument('--browser', default='/usr/bin/google-chrome')
    args = parser.parse_args()
    directory = args.directory.resolve()
    reports = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1500, 'height': 1100})
        context.route('https://**/*', lambda route: route.abort())
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        if args.only in (None, 'standalone'):
            path = (directory / 'standalone.html').as_uri()
            for family, controls in [('linear', ['m', 'q']), ('quadratic', ['a', 'b', 'c']), ('power', ['a', 'n'])]:
                page.goto(path + '?type=' + family)
                ready(page)
                expect(page.locator('input[name="function-type"]:checked')).to_have_value(family)
                assert page.locator('#parameters input[type="range"]').evaluate_all('(inputs)=>inputs.map(input=>input.id)') == ['slider-' + key for key in controls]
                assert page.locator('[name="function-type"]').count() == 3
            original = page.locator('#function-curve').get_attribute('d')
            slider(page, 'a', -2)
            slider(page, 'n', 4)
            expect(page.locator('#formula')).to_have_attribute('data-tex', 'f(x)=-2x^{4}')
            assert original != page.locator('#function-curve').get_attribute('d')
            page.screenshot(path=str(directory / 'desktop-power.png'), full_page=True)
            page.locator('[value="linear"]').check()
            slider(page, 'm', 2)
            slider(page, 'q', -3)
            expect(page.locator('#formula')).to_have_attribute('data-tex', 'f(x)=2x-3')
            page.locator('[value="quadratic"]').check()
            slider(page, 'a', 0)
            expect(page.locator('#insight')).to_have_attribute('data-special', 'true')
            page.locator('[value="power"]').check()
            expect(page.locator('#slider-n')).to_have_value('4')
            expect(page.locator('#slider-a')).to_have_value('-2')
            slider(page, 'a', 0)
            expect(page.locator('#insight')).to_contain_text('Nullfunktion')
            page.locator('#number-n').fill('2.5')
            page.locator('#number-n').press('Enter')
            expect(page.locator('#slider-n')).to_have_value('3')
            page.locator('#reset-parameters').click()
            expect(page.locator('#slider-a')).to_have_value('1')
            for _ in range(4):
                page.locator('#zoom-in').click()
            expect(page.locator('#zoom-in')).to_be_disabled()
            page.locator('#reset-view').click()
            page.reload(); ready(page)
            expect(page.locator('[value="power"]')).to_be_checked()
            page.goto(path + '?type=linear'); ready(page)
            expect(page.locator('[value="linear"]')).to_be_checked()
            expect(page.locator('#slider-q')).to_have_value('-3')
            page.locator('[value="linear"]').focus()
            page.keyboard.press('ArrowDown')
            expect(page.locator('[value="quadratic"]')).to_be_checked()
            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('[value="power"]').check()
            expect(page.locator('#formula')).to_have_attribute('data-tex', 'f(x)=x^{3}')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
            page.screenshot(path=str(directory / 'mobile-power.png'), full_page=True)
            page.set_viewport_size({'width': 1500, 'height': 1100})
            reports.append('standalone: three presets, all controls, parity, zero, keyboard, state, zoom, mobile')
        if args.only in (None, 'host'):
            page.goto((directory / 'host.html').as_uri())
            frame = app_frame(page)
            slider(frame, 'n', 11)
            slider(frame, 'a', -0.5)
            page.wait_for_function('fixture.state?.parameters.power.n===11 && fixture.state.parameters.power.a===-0.5')
            saved = page.evaluate('fixture.state')
            page.evaluate('state=>fixture.mount({state,activity:"power",presentation:"full",typography:{fontSizePt:13,lineHeight:1.6,scaleFactor:1.3}})', saved)
            frame = app_frame(page)
            expect(frame.locator('#slider-n')).to_have_value('11')
            expect(frame.locator('#formula')).to_have_attribute('data-tex', 'f(x)=-0.5x^{11}')
            assert frame.evaluate('MuWeaveModuleBridge.getTypography().fontSizePt') == 13
            assert frame.evaluate('getComputedStyle(document.body).fontSize') == '17.3333px'
            for family in ['linear', 'quadratic', 'power']:
                page.evaluate('activity=>fixture.mount({activity})', family)
                frame = app_frame(page)
                expect(frame.locator('[name="function-type"]:checked')).to_have_value(family)
            page.evaluate('fixture.send("host-disabled",{reason:"verification"})')
            expect(frame.locator('#slider-a')).to_be_disabled()
            expect(frame.locator('#notice')).to_contain_text('gesperrt')
            page.evaluate('fixture.mount({state:{schema:99}})')
            page.wait_for_timeout(500)
            frame = next(frame for frame in page.frames[1:] if frame.locator('#app').count())
            expect(frame.locator('#notice')).to_contain_text('ungültig')
            assert page.evaluate('fixture.state.schema') == 99
            reports.append('host: opaque sandbox, each activity, compact/full, snapshot restore, typography, disabled and invalid state')
        if args.only in (None, 'pyhtml'):
            page.goto((directory / 'smoke.html').as_uri())
            frame = app_frame(page)
            expect(frame.locator('[value="power"]')).to_be_checked()
            slider(frame, 'n', 6)
            expect(frame.locator('#formula')).to_have_attribute('data-tex', 'f(x)=x^{6}')
            assert page.locator('#muweave-mathjax').count() == 1
            assert page.locator('#muweave-runtime-profiles').count() == 1
            page.screenshot(path=str(directory / 'pyhtml.png'), full_page=True)
            with context.expect_page() as pending:
                page.locator('[data-muweave-applet-open]').click()
            popup = pending.value
            popup.on('pageerror', lambda error: errors.append(str(error)))
            popup.wait_for_load_state()
            child = app_frame(popup)
            expect(child.locator('[value="quadratic"]')).to_be_checked()
            slider(child, 'a', -2)
            slider(child, 'c', 3)
            expect(child.locator('#formula')).to_have_attribute('data-tex', 'f(x)=-2x^{2}+3')
            popup.locator('[data-applet-fullscreen]:visible').click()
            expect(popup.locator('.muweave-applet-fullscreen')).to_have_count(1)
            expect(child.locator('#slider-a')).to_have_value('-2')
            popup.locator('[data-applet-exit]:visible').click()
            expect(popup.locator('.muweave-applet-fullscreen')).to_have_count(0)
            expect(child.locator('#slider-c')).to_have_value('3')
            if popup.evaluate('document.documentElement.scrollHeight > innerHeight + 20'):
                popup.evaluate('scrollTo(0,0)')
                child.locator('#plot').hover()
                popup.mouse.wheel(0, 400)
                popup.wait_for_function('() => scrollY > 0')
            popup.screenshot(path=str(directory / 'linked-applet.png'), full_page=True)
            popup.close()
            reports.append('pyhtml: offline iframe and launch link, selected family, fullscreen preserves controls, wheel scroll, one shared runtime')
        if args.only in (None, 'failures'):
            for filename, message in [('no-runtime.html', 'Formeldarstellung'), ('mixed-version.html', 'verschiedenen Versionen')]:
                page.goto((directory / filename).as_uri())
                expect(page.locator('#notice')).to_contain_text(message)
                expect(page.locator('[value="power"]')).to_be_disabled()
            reports.append('failures: missing runtime and stale assets visibly stop startup')
        assert not errors, errors
        print(json.dumps({'passed': reports, 'pageErrors': errors}, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == '__main__':
    main()
