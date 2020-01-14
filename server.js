const http = require("http");
var amqp = require('amqplib/callback_api');
const uuidv1 = require('uuid/v1');
var response_map = new Map();
// var second_object;

function res_func2 (data_msg, response) {
  let msg = 'data' + ':' + data_msg;
  response.write(msg);
  response.write("\n\n");
};

amqp.connect('amqp://hwa125:960923@localhost', function(err, conn) {
  conn.createChannel(function(err, ch) {
    var q = 'predict-second';

    ch.assertQueue(q, {durable: false});
    console.log(" [*] Waiting for messages in %s. To exit press CTRL+C", q);
    ch.consume(q, function(msg) {

      let data_msg = msg.content.toString()

      response_map.forEach((res) => res_func2(data_msg, res));

    }, {noAck: true});
  });
});

http
  .createServer((request, response)  => {
    console.log("Requested url: " + request.url);

    if (request.url.toLowerCase() === "/get_second") {
      const uuid = uuidv1();
      response.writeHead(200, {
        Connection: "keep-alive",
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*"
      });
      response_map.set(uuid, response);
      response.on('close', ()=>{response_map.delete(uuid)})
    }
  })
  .listen(80, () => {
    console.log("Server running at http://127.0.0.1:80/");
  });
