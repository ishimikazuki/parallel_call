import { BrowserRouter, Routes, Route } from "react-router-dom";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<div>ParallelDialer - Coming Soon</div>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
