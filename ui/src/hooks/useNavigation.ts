import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { readRoute, routeURL, type Route } from '../lib/navigation';
export function useNavigation() {
  const positions = useRef(new Map<string, number>());
  const activeURL = useRef(location.pathname + location.search);
  const [route, setRoute] = useState<Route>(() => ({
    ...readRoute(location.search),
    scroll: history.state?.scroll || 0,
  }));
  useEffect(() => {
    const previousRestoration = history.scrollRestoration;
    history.scrollRestoration = 'manual';
    history.replaceState({ ...history.state, firmly: true }, '', location.href);
    const pop = () => {
      activeURL.current = location.pathname + location.search;
      setRoute({
        ...readRoute(location.search),
        scroll: positions.current.get(activeURL.current) ?? history.state?.scroll ?? 0,
      });
    };
    let timer: ReturnType<typeof setTimeout>;
    const remember = () => {
      positions.current.set(activeURL.current, window.scrollY);
      clearTimeout(timer);
      const url = activeURL.current;
      timer = setTimeout(() => {
        if (url === activeURL.current)
          history.replaceState({ ...history.state, scroll: window.scrollY }, '', location.href);
      }, 100);
    };
    addEventListener('popstate', pop);
    addEventListener('scroll', remember, { passive: true });
    return () => {
      clearTimeout(timer);
      history.scrollRestoration = previousRestoration;
      removeEventListener('popstate', pop);
      removeEventListener('scroll', remember);
    };
  }, []);
  const navigate = useCallback((next: Route, replace = false) => {
    positions.current.set(activeURL.current, window.scrollY);
    history.replaceState({ ...history.state, scroll: window.scrollY }, '', location.href);
    const url = routeURL(next);
    const same = url === location.pathname + location.search;
    activeURL.current = url;
    history[replace || same ? 'replaceState' : 'pushState'](
      { firmly: true, scroll: next.scroll },
      '',
      url,
    );
    setRoute(next);
  }, []);
  useLayoutEffect(() => {
    if (route.page === 'report') return; // The lazy report restores after its content is mounted.
    const frame = requestAnimationFrame(() => scrollTo({ top: route.scroll, behavior: 'instant' }));
    return () => cancelAnimationFrame(frame);
  }, [route.page, route.job, route.sample, route.scroll]);
  return { route, navigate };
}
