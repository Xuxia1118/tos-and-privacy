export default async function handler(req, res) {
  const railwayCallback = 'https://tos-and-privacy-production.up.railway.app/';

  const url = railwayCallback + (req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '');

  try {
    const response = await fetch(url, { method: 'GET' });
    const text = await response.text();
    res.status(response.status).send(text);
  } catch (err) {
    console.error(err);
    res.status(500).send('Proxy Error');
  }
}
