import { render } from 'preact';
import '@fontsource/onest/400.css';
import '@fontsource/onest/500.css';
import '@fontsource/onest/600.css';
import '@fontsource/onest/700.css';
import './ui/styles.css';
import { App } from './ui/App';

render(<App />, document.getElementById('root')!);
