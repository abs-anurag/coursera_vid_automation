from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SelectorSet:
    login_url_patterns: tuple[re.Pattern[str], ...] = field(
        default=(
            re.compile(r"accounts\.coursera\.org", re.I),
            re.compile(r"/login", re.I),
            re.compile(r"/signin", re.I),
        )
    )
    course_url_pattern: re.Pattern[str] = re.compile(r"https?://(?:www\.)?coursera\.org/learn/([^/?#]+)", re.I)
    lecture_url_pattern: re.Pattern[str] = re.compile(r"/learn/[^/]+/lecture/", re.I)
    quiz_url_pattern: re.Pattern[str] = re.compile(
        r"/learn/[^/]+/(quiz|exam|practice|ungradedLti|gradedLti)/",
        re.I,
    )
    reading_url_pattern: re.Pattern[str] = re.compile(
        r"/learn/[^/]+/(supplement|ungradedWidget|discussionPrompt)/",
        re.I,
    )
    assignment_url_pattern: re.Pattern[str] = re.compile(
        r"/learn/[^/]+/(assignment|programming|programmingAssignment|peer|lab|ungradedLab|workspaceLab|honors|staffGraded|review|notebook)/",
        re.I,
    )
    item_link_pattern: re.Pattern[str] = re.compile(
        r"/learn/[^/]+/(lecture|quiz|exam|practice|supplement|assignment|programming|peer|lab|honors)/[^/?#]+",
        re.I,
    )

    video_elements: tuple[str, ...] = (
        "video",
        "video.vjs-tech",
        ".video-js video",
        "[data-track-component='video_player'] video",
        ".rc-VideoPlayerManager video",
    )
    video_containers: tuple[str, ...] = (
        ".video-js",
        ".vjs-tech",
        ".rc-VideoPlayerManager",
        "[data-testid='video-player']",
        "[aria-label*='Video player' i]",
    )
    play_buttons: tuple[str, ...] = (
        "button.vjs-big-play-button",
        "button.vjs-play-control",
        "button[title='Play']",
        "button[aria-label='Play']",
        "button[aria-label*='Play' i]",
        ".rc-VideoControlsContainer button",
    )
    pause_buttons: tuple[str, ...] = (
        "button[title='Pause']",
        "button[aria-label='Pause']",
        "button.vjs-playing",
    )
    next_buttons: tuple[str, ...] = (
        "button:has-text('Next')",
        "a:has-text('Next')",
        "button:has-text('Continue')",
        "a:has-text('Continue')",
        "[data-track-component='next_item']",
        "[aria-label*='Next Item' i]",
    )
    course_nav_links: tuple[str, ...] = (
        "nav a[href*='/learn/']",
        "[data-testid='navigation-container'] a[href*='/learn/']",
        ".rc-ItemDrawer a[href*='/learn/']",
        "a[href*='/lecture/']",
        "a[href*='/quiz/']",
        "a[href*='/supplement/']",
    )
    completed_markers: tuple[str, ...] = (
        "[data-testid='completed-icon']",
        "[aria-label*='Completed' i]",
        "[aria-label*='complete' i]",
        "svg[aria-label*='Completed' i]",
        ".rc-WeekItemCompleted",
    )
    quiz_signals: tuple[str, ...] = (
        "button:has-text('Submit')",
        "button:has-text('Check answers')",
        "form [role='radiogroup']",
        "[data-testid='quiz-layout']",
        "text=/Honor Code/i",
    )
    reading_signals: tuple[str, ...] = (
        "[data-testid='cml-viewer']",
        "article",
        "text=/Reading/i",
    )
    assignment_signals: tuple[str, ...] = (
        "button:has-text('Submit assignment')",
        "text=/peer-graded/i",
        "text=/programming assignment/i",
        "text=/Honor Code/i",
    )
    popup_dismiss: tuple[str, ...] = (
        "button:has-text('Accept')",
        "button:has-text('I agree')",
        "button:has-text('Got it')",
        "button:has-text('No thanks')",
        "button:has-text('Close')",
        "button[aria-label='Close']",
        "#onetrust-accept-btn-handler",
    )
    course_title: tuple[str, ...] = (
        "h1",
        "[data-e2e='hero-title']",
        "nav [data-track-component='course_name']",
        "a[href*='/learn/'][data-click-key*='course']",
    )
    login_text: tuple[str, ...] = (
        "text=/Log in/i",
        "text=/Welcome back/i",
        "input[type='email']",
        "input[name='email']",
    )


SELECTORS = SelectorSet()
