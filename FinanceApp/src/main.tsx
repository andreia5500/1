import { render } from 'preact';
import '@fontsource/fira-sans-condensed/latin-400.css';
import '@fontsource/fira-sans-condensed/latin-600.css';
import '@fontsource/fira-sans-condensed/latin-ext-400.css';
import '@fontsource/fira-sans-condensed/latin-ext-600.css';
import '@fontsource/fira-sans-condensed/cyrillic-400.css';
import '@fontsource/fira-sans-condensed/cyrillic-600.css';
import '@fontsource/fira-sans/latin-400.css';
import '@fontsource/fira-sans/latin-600.css';
import '@fontsource/fira-sans/latin-ext-400.css';
import '@fontsource/fira-sans/latin-ext-600.css';
import '@fontsource/fira-sans/cyrillic-400.css';
import '@fontsource/fira-sans/cyrillic-600.css';
import './ui/styles.css';
import { App } from './ui/App';

render(<App />, document.getElementById('root')!);
