import claims from '../../../data/published.json';
export function GET(){return new Response(JSON.stringify(claims,null,2),{headers:{'Content-Type':'application/json; charset=utf-8'}})}
