function r(a){return a.estado==="resuelto"||a.estado==="falsa_alarma"?"normal":a.confianza_ia>=.8?"critica":"moderada"}export{r as a};
