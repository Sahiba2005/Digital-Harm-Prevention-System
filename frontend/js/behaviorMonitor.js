/*let clicks=0

document.addEventListener("click",function(){

clicks++

if(clicks>10){
console.log("Suspicious rapid clicking detected")
}

})*/
let clicks=0
let startTime = Date.now()

document.addEventListener("click",function(){

clicks++

let elapsed = (Date.now() - startTime)/1000

let rate = clicks / elapsed

if(rate > 5){
console.log("Suspicious rapid clicking detected")
}

})