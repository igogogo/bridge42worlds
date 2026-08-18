/* Структурированные данные учебного раздела (Schema.org) — задача архитектора 18.08.
 *
 * Что размечаем:
 *   · страница темы  → Course (+ hasCourseInstance, бесплатный доступ, язык страницы);
 *   · дерево знаний  → ItemList курсов;
 *   · страница параграфа → Quiz с вопросами, которые читатель ВИДИТ на странице.
 *
 * Чего НЕ делаем: не подставляем правильные ответы. На странице они скрыты до того, как
 * читатель ответит сам, и вытаскивать их в разметку — значит отдать поисковику то, что
 * спрятано от человека. Google для Education Q&A ждёт `acceptedAnswer`, поэтому такой
 * фрагмент он засчитает частично; это осознанный размен в пользу читателя, решение
 * пересматривается одной строкой (ANSWERS_IN_MARKUP).
 *
 * Статьи не трогаем: у них своя разметка из build_jsonld в generate.py.
 */
(function (global) {
    'use strict';

    var ANSWERS_IN_MARKUP = false;         // см. комментарий выше
    var SITE = 'https://bridge42worlds.com';

    var ORG = {
        '@type': 'Organization',
        name: 'bridge42worlds',
        url: SITE
    };

    function put(data) {
        if (!data) return;
        var s = document.createElement('script');
        s.type = 'application/ld+json';
        s.textContent = JSON.stringify(data, null, 1);
        document.head.appendChild(s);
    }

    function lang() { return global.B42_LANG || 'ru'; }

    /** Страница темы: сам курс. */
    function course(topicId, branch, lessonCount) {
        if (!branch || !branch.title) return;
        put({
            '@context': 'https://schema.org',
            '@type': 'Course',
            name: branch.title,
            description: branch.lead || branch.subtitle || '',
            inLanguage: lang(),
            url: SITE + '/course.html?t=' + topicId + '&lang=' + lang(),
            provider: ORG,
            isAccessibleForFree: true,
            numberOfCredits: undefined,
            hasCourseInstance: {
                '@type': 'CourseInstance',
                courseMode: 'online',
                courseWorkload: lessonCount ? 'PT' + (lessonCount * 75) + 'M' : undefined,
                inLanguage: lang()
            }
        });
    }

    /** Дерево знаний: список курсов по порядку тем. */
    function courseList(topics) {
        if (!topics || !topics.length) return;
        put({
            '@context': 'https://schema.org',
            '@type': 'ItemList',
            name: 'bridge42worlds',
            inLanguage: lang(),
            numberOfItems: topics.length,
            itemListElement: topics.map(function (t, i) {
                return {
                    '@type': 'ListItem',
                    position: i + 1,
                    item: {
                        '@type': 'Course',
                        name: t.title,
                        description: t.sub || '',
                        url: SITE + '/course.html?t=' + t.id + '&lang=' + lang(),
                        inLanguage: lang(),
                        provider: ORG,
                        isAccessibleForFree: true
                    }
                };
            })
        });
    }

    /** Параграф: испытание. Берём только вопросы, видимые на странице. */
    function quiz(lessonTitle, questions) {
        var qs = (questions || []).filter(function (q) { return q && q.q; });
        if (!qs.length) return;
        put({
            '@context': 'https://schema.org',
            '@type': 'Quiz',
            name: lessonTitle,
            inLanguage: lang(),
            about: { '@type': 'Thing', name: lessonTitle },
            hasPart: qs.map(function (q) {
                var node = {
                    '@type': 'Question',
                    eduQuestionType: q.type === 'mcq' ? 'Multiple choice' : 'Flashcard',
                    text: q.q,
                    inLanguage: lang()
                };
                if (q.type === 'mcq' && (q.options || []).length) {
                    node.suggestedAnswer = q.options.map(function (o, i) {
                        var a = { '@type': 'Answer', text: o };
                        if (ANSWERS_IN_MARKUP && i === q.answer) a['@type'] = 'Answer';
                        return a;
                    });
                    if (ANSWERS_IN_MARKUP && typeof q.answer === 'number') {
                        node.acceptedAnswer = { '@type': 'Answer', text: q.options[q.answer] };
                    }
                }
                return node;
            })
        });
    }

    global.B42JsonLd = { course: course, courseList: courseList, quiz: quiz };
})(window);
