import { useCallback, useRef } from 'react';
import { HOME, type Route } from '../lib/navigation';

export function useSettingsNavigation(
  route: Route,
  go: (route: Route, replace?: boolean) => void,
  completed: boolean,
) {
  const returnTo = useRef<Route>(
    route.page === 'settings'
      ? { ...route, page: route.sample ? 'report' : route.job ? 'progress' : 'home' }
      : HOME,
  );
  const rememberReturn = useCallback((current: Route) => {
    returnTo.current = { ...current, scroll: window.scrollY };
  }, []);
  const closeSettings = () => {
    if (history.state?.settingsFromApp) {
      history.back();
      return;
    }
    const target = returnTo.current;
    go(target.page === 'progress' && completed ? { ...target, page: 'report' } : target);
  };
  return { rememberReturn, closeSettings };
}
