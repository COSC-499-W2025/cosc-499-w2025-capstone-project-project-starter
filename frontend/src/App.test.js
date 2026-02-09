import { render, screen } from '@testing-library/react';
import App from './App';

test('renders authentication tabs', () => {
  render(<App />);
  expect(screen.getByText(/log in/i)).toBeInTheDocument();
  expect(screen.getByText(/create account/i)).toBeInTheDocument();
});
